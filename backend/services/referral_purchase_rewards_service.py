"""Tier C1 — referrer coins when a referred user completes a qualifying first purchase."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SOCIAL_PATH = os.path.join(_BASE, "data", "social_structure.json")

_DEFAULT_REWARDS = {
    "coin_pack": {"referrer_coins": 100},
    "hosting": {"referrer_coins": 150},
    "bundle": {"referrer_coins": 125},
    "shop_item": {"referrer_coins": 75},
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _reward_cfg(kind: str) -> Dict[str, Any]:
    try:
        from backend.services.monetization_config_service import _load_raw

        raw = _load_raw()
        table = raw.get("referral_purchase_rewards") or {}
        row = table.get(kind) if isinstance(table, dict) else None
        if isinstance(row, dict) and int(row.get("referrer_coins") or 0) > 0:
            return row
    except Exception:
        pass
    return dict(_DEFAULT_REWARDS.get(kind) or {"referrer_coins": 50})


def _load_social() -> dict:
    if not os.path.isfile(_SOCIAL_PATH):
        return {"referrals": {"codes": {}, "signups": []}}
    try:
        with open(_SOCIAL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"referrals": {"codes": {}, "signups": []}}
        data.setdefault("referrals", {"codes": {}, "signups": []})
        return data
    except Exception:
        return {"referrals": {"codes": {}, "signups": []}}


def _save_social(data: dict) -> None:
    os.makedirs(os.path.dirname(_SOCIAL_PATH), exist_ok=True)
    tmp = _SOCIAL_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _SOCIAL_PATH)


def _find_referral_for_buyer(buyer_user_id: str) -> Optional[dict]:
    buyer_user_id = (buyer_user_id or "").strip()
    if not buyer_user_id:
        return None
    social = _load_social()
    signups = (social.get("referrals") or {}).get("signups") or []
    for row in signups:
        if isinstance(row, dict) and row.get("referred_user_id") == buyer_user_id:
            return row
    return None


def classify_purchase(*, item_id: str = "", product: str = "", is_coin_pack: bool = False) -> str:
    iid = (item_id or "").strip().lower()
    prod = (product or "").strip().lower()
    if is_coin_pack or iid.startswith("coin-pack") or iid.startswith("overage-pack"):
        return "coin_pack"
    if iid.startswith("mn2-pack"):
        return "mn2_pack"
    if prod == "mn2_masternode_hosting" or iid.startswith("mnq_"):
        return "hosting"
    if iid.startswith("bundle-"):
        return "bundle"
    return "shop_item"


def maybe_reward_referrer(
    buyer_user_id: str,
    *,
    purchase_kind: str,
    item_id: str = "",
    order_id: str = "",
    amount_usd: float = 0,
) -> Dict[str, Any]:
    """Credit referrer once when referred user completes first qualifying purchase."""
    buyer_user_id = (buyer_user_id or "").strip()
    if not buyer_user_id:
        return {"success": False, "error": "missing_buyer"}

    referral = _find_referral_for_buyer(buyer_user_id)
    if not referral:
        return {"success": True, "rewarded": False, "reason": "no_referrer"}

    if referral.get("purchase_rewarded_at"):
        return {"success": True, "rewarded": False, "reason": "already_rewarded", "duplicate": True}

    referrer_id = (referral.get("referrer_user_id") or "").strip()
    if not referrer_id or referrer_id == buyer_user_id:
        return {"success": False, "error": "invalid_referrer"}

    cfg = _reward_cfg(purchase_kind)
    coins = int(cfg.get("referrer_coins") or 0)
    if coins <= 0:
        return {"success": True, "rewarded": False, "reason": "zero_reward"}

    ref_key = f"referral-purchase-{referral.get('id') or buyer_user_id}"
    try:
        from backend.services.unified_points_database import unified_points_db

        result = unified_points_db.add_points(
            referrer_id,
            "coins",
            float(coins),
            source="referral_purchase_reward",
            metadata={
                "buyer_user_id": buyer_user_id,
                "purchase_kind": purchase_kind,
                "item_id": item_id,
                "order_id": order_id,
                "amount_usd": amount_usd,
                "reference": ref_key,
            },
        )
        if not result.get("success") and not result.get("duplicate"):
            return {"success": False, "error": result.get("error", "award_failed")}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    social = _load_social()
    for row in (social.get("referrals") or {}).get("signups") or []:
        if row.get("referred_user_id") == buyer_user_id:
            row["purchase_rewarded_at"] = _iso()
            row["purchase_reward_kind"] = purchase_kind
            row["purchase_reward_coins"] = coins
            row["purchase_order_id"] = order_id
            break
    _save_social(social)

    try:
        from backend.routes.social_routes import push_activity

        push_activity(
            referrer_id,
            "referral_purchase_reward",
            f"+{coins} coins — referral completed first purchase",
            {"buyer_user_id": buyer_user_id, "coins": coins, "kind": purchase_kind},
        )
    except Exception:
        pass

    return {
        "success": True,
        "rewarded": True,
        "referrer_user_id": referrer_id,
        "referrer_coins": coins,
        "purchase_kind": purchase_kind,
    }
