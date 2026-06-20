"""
Tier B product bundles — on-ramp+hosting, auction fee info, copy-trading premium.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _tier_b_config() -> Dict[str, Any]:
    try:
        from backend.services.monetization_config_service import get_shop_monetization

        sm = get_shop_monetization()
        tb = sm.get("tier_b")
        return dict(tb) if isinstance(tb, dict) else {}
    except Exception:
        return {}


def get_onramp_hosting_offer(user_id: str) -> Dict[str, Any]:
    """B2 — sequenced MN2 on-ramp then hosting slot with bundle discount."""
    cfg = (_tier_b_config().get("onramp_hosting") or {})
    window_days = int(cfg.get("window_days") or 7)
    discount = int(cfg.get("hosting_discount_percent") or 10)
    promo = (cfg.get("promo_code") or "HOSTMN5").strip()
    uid = (user_id or "").strip()
    recent_onramp = user_has_recent_onramp(uid, window_days=window_days)
    last_onramp_at = _last_onramp_at(uid, window_days=window_days)
    hosting_done = user_has_paid_hosting(uid)
    auto_promo = promo if recent_onramp and not hosting_done else None
    return {
        "success": True,
        "user_id": uid,
        "eligible_for_hosting_step": recent_onramp,
        "hosting_step_done": hosting_done,
        "last_onramp_at": last_onramp_at,
        "window_days": window_days,
        "hosting_discount_percent": discount,
        "promo_code": promo,
        "auto_promo_code": auto_promo,
        "next_href": "/shop?tab=mn2&bundle=hosting",
        "steps": [
            {
                "step": 1,
                "title": "Buy MN2 (PayPal on-ramp)",
                "done": recent_onramp,
                "href": "/profile#mn2-wallet",
                "cta": "Get MN2 quote",
            },
            {
                "step": 2,
                "title": "Reserve masternode hosting",
                "done": hosting_done,
                "href": "/shop?tab=mn2&bundle=hosting",
                "cta": "Host from $4.99/slot",
                "discount_note": (
                    f"Promo {auto_promo} auto-applies ({discount}% off hosting PayPal checkout)"
                    if auto_promo
                    else (f"Complete step 1 first — then use {promo} at checkout" if not recent_onramp else None)
                ),
            },
        ],
    }


def user_has_recent_onramp(user_id: str, *, window_days: int = 7) -> bool:
    return _last_onramp_at(user_id, window_days=window_days) is not None


def _last_onramp_at(user_id: str, *, window_days: int = 7) -> Optional[str]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return None
    try:
        from backend.services.mn2_onramp_service import get_user_orders

        orders = (get_user_orders(uid, limit=20).get("orders") or [])
        cutoff = _utcnow() - timedelta(days=int(window_days or 7))
        for o in orders:
            if o.get("status") not in ("held", "cleared"):
                continue
            created = o.get("created_at") or ""
            try:
                dt = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            except Exception:
                continue
            if dt >= cutoff:
                return created
    except Exception:
        pass
    return None


def user_has_paid_hosting(user_id: str) -> bool:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return False
    try:
        from backend.services.mn2_masternode_hosting_service import list_user_orders

        return any(o.get("status") == "paid" for o in list_user_orders(uid, limit=50))
    except Exception:
        return False


def get_auto_hosting_promo(user_id: str) -> Optional[str]:
    """Return bundle promo when user completed on-ramp within window and has not paid hosting yet."""
    offer = get_onramp_hosting_offer(user_id)
    return offer.get("auto_promo_code")


def get_auction_fee_info() -> Dict[str, Any]:
    """B5 — expose enforced marketplace fee (already applied in shop_auction_service)."""
    try:
        from backend.services.shop_auction_service import MARKETPLACE_FEE_RATE

        rate = float(MARKETPLACE_FEE_RATE)
    except Exception:
        rate = 0.05
    cfg = (_tier_b_config().get("auction") or {})
    return {
        "success": True,
        "fee_rate": rate,
        "fee_percent": round(rate * 100, 2),
        "description": cfg.get("description") or "Platform fee on player-to-player auction sales.",
        "enforced": True,
    }


def get_copy_trading_premium_status(user_id: str) -> Dict[str, Any]:
    """B7 — monthly follow-top-trader premium lane."""
    cfg = (_tier_b_config().get("copy_trading_premium") or {})
    try:
        from backend.services.mn2_copy_trading import get_premium_status

        st = get_premium_status(user_id)
    except Exception:
        st = {"active": False}
    return {
        "success": True,
        "user_id": user_id,
        "active": bool(st.get("active")),
        "expires_at": st.get("expires_at"),
        "price_usd": float(cfg.get("price_usd") or 4.99),
        "price_coins": int(cfg.get("price_coins") or 499),
        "duration_days": int(cfg.get("duration_days") or 30),
        "perks": cfg.get("perks") or [
            "Higher copy scale (up to 50%)",
            "Priority mirror on leader rewards",
            "Premium badge on trader profile",
        ],
    }


def purchase_copy_trading_premium(user_id: str, *, source: str = "shop_coins") -> Dict[str, Any]:
    cfg = (_tier_b_config().get("copy_trading_premium") or {})
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "account_required"}
    if source == "paypal":
        try:
            from backend.services.mn2_copy_trading import activate_premium

            return activate_premium(uid, days=int(cfg.get("duration_days") or 30), source="paypal")
        except Exception as e:
            return {"success": False, "error": str(e)}
    price = int(cfg.get("price_coins") or 499)
    try:
        from backend.services.shop_monetization_service import _charge

        ok, err = _charge(uid, price, payment_method="coins", source="copy_trading_premium", metadata={})
        if not ok:
            return {"success": False, "error": err or "insufficient_coins"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    from backend.services.mn2_copy_trading import activate_premium

    return activate_premium(uid, days=int(cfg.get("duration_days") or 30), source=source)
