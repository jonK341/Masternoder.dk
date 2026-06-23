"""
Subscription overage — PayPal top-up SKUs when monthly allowance is running low.

§8.2 overage policy: priced above blended COGS; surfaced at 80%+ allowance use
or on generator 402 insufficient credits for subscribed users.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services.monetization_allowance_service import get_user_usage_allowance
from backend.services.monetization_config_service import (
    get_overage_packs,
    get_overage_policy,
    is_overage_pack,
)


def _shortfall_credits(summary: Dict[str, Any]) -> float:
    sub = summary.get("subscription") or {}
    if not sub.get("has_subscription"):
        return 0.0
    try:
        monthly = float(sub.get("monthly_generation_credits") or 0)
    except (TypeError, ValueError):
        monthly = 0.0
    if monthly <= 0:
        return 0.0
    metering = summary.get("metering") or {}
    try:
        used = float(metering.get("generation_credits_used") or 0)
    except (TypeError, ValueError):
        used = 0.0
    return max(0.0, round(used - monthly, 2))


def _recommend_pack_id(
    packs: List[Dict[str, Any]],
    *,
    shortfall: float,
    required_credits: Optional[float] = None,
) -> Optional[str]:
    if not packs:
        return None
    need = max(shortfall, float(required_credits or 0), 0.0)
    if need <= 0:
        return str(packs[0].get("id") or "") or None
    sorted_packs = sorted(
        packs,
        key=lambda p: float(p.get("generation_credits_granted") or 0),
    )
    for p in sorted_packs:
        try:
            gc = float(p.get("generation_credits_granted") or 0)
        except (TypeError, ValueError):
            gc = 0.0
        if gc >= need:
            return str(p.get("id") or "") or None
    last = sorted_packs[-1]
    return str(last.get("id") or "") or None


def should_offer_overage(summary: Dict[str, Any]) -> bool:
    """True when user has a sub and usage crossed the configured threshold."""
    sub = summary.get("subscription") or {}
    if not sub.get("has_subscription"):
        return False
    policy = get_overage_policy()
    try:
        threshold = float(policy.get("show_offers_from_percent") or 80)
    except (TypeError, ValueError):
        threshold = 80.0
    nudge = summary.get("nudge") or {}
    level = str(nudge.get("nudge_level") or "")
    if level in ("warning", "upsell"):
        return True
    pct = nudge.get("percent_of_monthly_allowance")
    if pct is not None and float(pct) >= threshold:
        return True
    return _shortfall_credits(summary) > 0


def get_overage_offers(
    user_id: str,
    *,
    period_days: int = 30,
    required_credits: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Overage SKUs + recommendation for PayPal one-click top-up.

    required_credits: optional immediate need (e.g. from generator entitlement check).
    """
    uid = (user_id or "").strip()
    if not uid or uid.lower() == "default_user":
        return {"success": False, "error": "user_id_required"}

    summary = get_user_usage_allowance(uid, period_days=period_days)
    if not summary.get("success"):
        return summary

    packs = get_overage_packs()
    shortfall = _shortfall_credits(summary)
    offer = should_offer_overage(summary) or (
        required_credits is not None and float(required_credits) > 0
        and (summary.get("subscription") or {}).get("has_subscription")
    )
    recommended = _recommend_pack_id(
        packs,
        shortfall=shortfall,
        required_credits=required_credits,
    )

    public_packs: List[Dict[str, Any]] = []
    for p in packs:
        public_packs.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "description": p.get("description"),
            "price_usd": p.get("price_usd"),
            "generation_credits_granted": p.get("generation_credits_granted"),
            "coins_granted": p.get("coins_granted"),
            "reference_eq_label": p.get("reference_eq_label"),
            "icon": p.get("icon"),
            "tag": p.get("tag"),
        })

    return {
        "success": True,
        "user_id": uid,
        "overage_eligible": offer,
        "shortfall_generation_credits": shortfall,
        "recommended_pack_id": recommended,
        "packs": public_packs if offer else [],
        "allowance": {
            "nudge": summary.get("nudge"),
            "subscription": summary.get("subscription"),
            "metering": summary.get("metering"),
            "wallet_generation_credits": summary.get("wallet_generation_credits"),
        },
        "checkout_hint": {
            "create_order": "POST /api/paypal/create-order",
            "shop_tab": "coins",
        },
    }


def build_entitlement_upsell(
    user_id: str,
    *,
    required_credits: float,
    available_credits: float,
) -> Dict[str, Any]:
    """Upsell block for HTTP 402 responses (generator + unified API)."""
    offers = get_overage_offers(
        user_id,
        required_credits=max(0.0, float(required_credits) - float(available_credits)),
    )
    upsell: Dict[str, Any] = {
        "reason": "insufficient_generation_credits",
        "required_credits": required_credits,
        "available_credits": available_credits,
        "shop_url": "/shop?category=buy_coins",
    }
    if offers.get("success") and offers.get("overage_eligible") and offers.get("packs"):
        upsell["reason"] = "subscription_overage"
        upsell["recommended_pack_id"] = offers.get("recommended_pack_id")
        upsell["overage_packs"] = offers.get("packs")
        upsell["shop_url"] = "/shop?category=buy_coins#overage"
    else:
        upsell["coin_packs_url"] = "/api/shop/coin-packs"
    return upsell
