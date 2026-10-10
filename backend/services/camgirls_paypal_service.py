"""PayPal checkout for camgirls unlock, tips, and gifts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ORDERS_PATH = os.path.join(_ROOT, "data", "camgirls_paypal_orders.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_orders() -> Dict[str, Any]:
    if not os.path.isfile(_ORDERS_PATH):
        return {"pending": {}, "captured": {}}
    try:
        with open(_ORDERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("pending", {})
            data.setdefault("captured", {})
            return data
    except Exception:
        pass
    return {"pending": {}, "captured": {}}


def _write_orders(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_ORDERS_PATH), exist_ok=True)
    with open(_ORDERS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _mn2_usd() -> float:
    try:
        from backend.services.crypto_exchange_service import _mn2_usd as rate
        return max(float(rate()), 0.01)
    except Exception:
        return 0.05


def _mn2_to_usd(amount_mn2: float) -> float:
    return round(max(float(amount_mn2), 0) * _mn2_usd(), 2)


def _resolve_mn2_amount(action: str, performer_id: str, *, amount_mn2: Optional[float] = None, gift_id: Optional[str] = None) -> Dict[str, Any]:
    from backend.services.camgirls_service import _get_performer
    from backend.services.camgirls_studio_service import studio_catalog

    p = _get_performer(performer_id)
    if not p:
        return {"success": False, "error": "performer_not_found"}
    action = (action or "unlock").strip().lower()
    if action == "unlock":
        mn2 = float(p.get("unlock_price_mn2") or 10)
    elif action == "tip":
        mn2 = float(amount_mn2 or p.get("tip_min_mn2") or 5)
        if mn2 < float(p.get("tip_min_mn2") or 5):
            return {"success": False, "error": "below_minimum"}
    elif action == "gift":
        cat = studio_catalog()
        gifts = (cat.get("gifts") or {}) if cat.get("success") else {}
        gift = gifts.get(gift_id or "")
        if not gift:
            return {"success": False, "error": "gift_not_found"}
        mn2 = float(gift.get("price_mn2") or 5)
    else:
        return {"success": False, "error": "invalid_action"}
    usd = _mn2_to_usd(mn2)
    if usd < 0.5:
        usd = 0.5
    return {
        "success": True,
        "action": action,
        "performer_id": performer_id,
        "amount_mn2": mn2,
        "amount_usd": usd,
        "gift_id": gift_id,
    }


def quote_action(
    action: str,
    performer_id: str,
    *,
    amount_mn2: Optional[float] = None,
    gift_id: Optional[str] = None,
) -> Dict[str, Any]:
    out = _resolve_mn2_amount(action, performer_id, amount_mn2=amount_mn2, gift_id=gift_id)
    if not out.get("success"):
        return out
    return {
        "success": True,
        "action": out["action"],
        "performer_id": performer_id,
        "amount_mn2": out["amount_mn2"],
        "amount_usd": out["amount_usd"],
        "mn2_usd_rate": _mn2_usd(),
        "gift_id": gift_id,
    }


def create_paypal_order(
    user_id: str,
    action: str,
    performer_id: str,
    *,
    amount_mn2: Optional[float] = None,
    gift_id: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import _is_age_verified

    user_id = (user_id or "").strip() or "default_user"
    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required", "error": "18+ required"}
    quote = _resolve_mn2_amount(action, performer_id, amount_mn2=amount_mn2, gift_id=gift_id)
    if not quote.get("success"):
        return quote

    base_url = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    item_name = f"camgirls_{quote['action']}_{performer_id}"
    if quote.get("gift_id"):
        item_name += f"_{quote['gift_id']}"

    from backend.services.paypal_service import create_order as pp_create

    result = pp_create(
        quote["amount_usd"],
        currency="USD",
        item_name=item_name,
        return_url=f"{base_url}/camgirls/?paypal=success",
        cancel_url=f"{base_url}/camgirls/?paypal=cancel",
        metadata={
            "product": "camgirls",
            "action": quote["action"],
            "performer_id": performer_id,
            "amount_mn2": quote["amount_mn2"],
            "gift_id": gift_id,
        },
    )
    if not result.get("success"):
        return result

    order_id = result.get("order_id") or ""
    rows = _read_orders()
    rows.setdefault("pending", {})[order_id] = {
        "order_id": order_id,
        "user_id": user_id,
        "action": quote["action"],
        "performer_id": performer_id,
        "amount_mn2": quote["amount_mn2"],
        "amount_usd": quote["amount_usd"],
        "gift_id": gift_id,
        "approve_url": result.get("approve_url") or "",
        "created_at": _iso(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z"),
    }
    _write_orders(rows)
    return {
        "success": True,
        "order_id": order_id,
        "approve_url": result.get("approve_url"),
        "amount_usd": quote["amount_usd"],
        "amount_mn2": quote["amount_mn2"],
    }


def _fulfill_action(user_id: str, pending: Dict[str, Any], order_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import fulfill_external_payment

    return fulfill_external_payment(
        user_id,
        pending.get("performer_id") or "",
        pending.get("action") or "unlock",
        float(pending.get("amount_mn2") or 0),
        payment_ref=order_id,
        gift_id=pending.get("gift_id"),
    )


def fulfill_capture(order_id: str, *, user_id: str = "") -> Dict[str, Any]:
    order_id = (order_id or "").strip()
    if not order_id:
        return {"success": False, "error": "order_id required"}

    rows = _read_orders()
    if order_id in rows.get("captured", {}):
        return {"success": True, "already_fulfilled": True, **rows["captured"][order_id]}

    pending = (rows.get("pending") or {}).get(order_id)
    if not pending:
        return {"success": False, "error": "order_not_found"}

    uid = (user_id or pending.get("user_id") or "").strip()
    if pending.get("user_id") != uid:
        return {"success": False, "error": "user_mismatch"}

    from backend.services.paypal_service import capture_order

    capture = capture_order(order_id)
    if not capture.get("success"):
        return {"success": False, "error": capture.get("error", "capture_failed")}

    result = _fulfill_action(uid, pending, order_id)
    if not result.get("success"):
        return result

    try:
        from backend.services.monetization_ledger_service import append_payment_event

        append_payment_event(
            provider="paypal",
            user_id=uid,
            order_id=order_id,
            capture_id=capture.get("capture_id"),
            amount_usd=float(pending.get("amount_usd") or 0),
            currency="USD",
            item_id=f"camgirls_{pending.get('action')}",
            item_name=f"Camgirls {pending.get('action')} — {pending.get('performer_id')}",
            extra={"product": "camgirls", "performer_id": pending.get("performer_id"), "amount_mn2": pending.get("amount_mn2")},
        )
    except Exception:
        pass

    cap = {
        "order_id": order_id,
        "fulfilled_at": _iso(),
        "result": result,
        "pending": pending,
    }
    rows.setdefault("captured", {})[order_id] = cap
    rows.get("pending", {}).pop(order_id, None)
    _write_orders(rows)
    return {"success": True, **cap}
