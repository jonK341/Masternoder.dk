"""
Camgirls PayPal on-ramp — unlock / tip / gift (#4).

MN2 remains primary; PayPal for users without MN2 balance.
"""
from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PENDING = os.path.join(_BASE, "logs", "camgirls", "paypal_pending.json")


def _mn2_usd() -> float:
    raw = (os.environ.get("MN2_USD_PRICE") or os.environ.get("MN2_USD_PRICE_USD") or "0.001").strip()
    try:
        v = float(raw)
        return v if v > 0 else 0.001
    except (TypeError, ValueError):
        return 0.001


def _usd_from_mn2(mn2: float) -> float:
    return max(0.99, round(float(mn2) * _mn2_usd(), 2))


def _base_url() -> str:
    from flask import request

    base = (os.environ.get("BASE_URL") or "").strip().rstrip("/")
    if base.endswith("/vidgenerator"):
        base = base.rsplit("/vidgenerator", 1)[0]
    return base or request.url_root.rstrip("/")


def _save_pending(order_id: str, row: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_PENDING), exist_ok=True)
        data = {}
        if os.path.isfile(_PENDING):
            with open(_PENDING, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        if not isinstance(data, dict):
            data = {}
        data[order_id] = row
        with open(_PENDING, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _pop_pending(order_id: str) -> Optional[Dict[str, Any]]:
    try:
        if not os.path.isfile(_PENDING):
            return None
        with open(_PENDING, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        row = data.pop(order_id, None)
        with open(_PENDING, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return row if isinstance(row, dict) else None
    except Exception:
        return None


def quote_action(
    action: str,
    performer_id: str,
    *,
    amount_mn2: Optional[float] = None,
    gift_id: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import get_performer

    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    act = (action or "").strip().lower()
    usd = None
    if act == "unlock":
        mn2 = float(row.get("unlock_price_usd") or 0) or float(row.get("unlock_price_mn2") or 0)
        usd = float(row["unlock_price_usd"]) if row.get("unlock_price_usd") else _usd_from_mn2(mn2)
    elif act in ("tip", "gift"):
        if act == "gift" and gift_id:
            from backend.services.camgirls_studio_service import studio_catalog

            gifts = (studio_catalog().get("gifts") or {})
            g = gifts.get(gift_id) if isinstance(gifts, dict) else None
            if not g:
                return {"success": False, "error": "gift_not_found"}
            usd = _usd_from_mn2(float(g.get("mn2") or amount_mn2 or 0))
        else:
            amt = float(amount_mn2 or row.get("tip_min_mn2") or 1)
            usd = _usd_from_mn2(amt)
    else:
        return {"success": False, "error": "invalid_action"}
    return {
        "success": True,
        "action": act,
        "performer_id": performer_id,
        "price_usd": usd,
        "display_name": row.get("display_name"),
    }


def create_paypal_order(
    user_id: str,
    action: str,
    performer_id: str,
    *,
    amount_mn2: Optional[float] = None,
    gift_id: Optional[str] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "account_required", "code": "ACCOUNT_REQUIRED"}
    q = quote_action(action, performer_id, amount_mn2=amount_mn2, gift_id=gift_id)
    if not q.get("success"):
        return q
    item_id = f"camgirls-{q['action']}-{performer_id}"
    if gift_id:
        item_id += f"-{gift_id}"
    base = _base_url()
    return_url = f"{base}/camgirls/?paypal=success&order_pending=1&user_id={urllib.parse.quote(uid)}"
    cancel_url = f"{base}/camgirls/?paypal=cancel"
    try:
        from backend.services.paypal_service import create_order

        result = create_order(
            amount=float(q["price_usd"]),
            currency="USD",
            item_name=f"Camgirls {q['action']} — {q.get('display_name') or performer_id}",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": item_id, "user_id": uid, "product": "camgirls"},
        )
    except Exception as e:
        return {"success": False, "error": str(e)}
    if not result.get("success"):
        return result
    oid = result.get("order_id")
    _save_pending(
        oid,
        {
            "user_id": uid,
            "action": q["action"],
            "performer_id": performer_id,
            "gift_id": gift_id,
            "amount_mn2": amount_mn2,
            "price_usd": q["price_usd"],
            "item_id": item_id,
        },
    )
    return {
        "success": True,
        "order_id": oid,
        "approve_url": result.get("approve_url"),
        "price_usd": q["price_usd"],
        "item_id": item_id,
    }


def fulfill_capture(order_id: str, *, user_id: Optional[str] = None) -> Dict[str, Any]:
    from backend.services.paypal_service import capture_order

    pending = _pop_pending(order_id)
    if not pending:
        return {"success": False, "error": "unknown_order"}
    cap = capture_order(order_id)
    if not cap.get("success"):
        _save_pending(order_id, pending)
        return cap
    uid = (user_id or pending.get("user_id") or "").strip()
    act = pending.get("action")
    pid = pending.get("performer_id")
    try:
        from backend.services.monetization_ledger_service import append_payment_event

        append_payment_event(
            provider="paypal",
            user_id=uid,
            order_id=order_id,
            capture_id=cap.get("capture_id"),
            amount_usd=float(cap.get("amount") or pending.get("price_usd") or 0),
            currency=str(cap.get("currency") or "USD"),
            item_id=pending.get("item_id") or "",
            item_name=f"camgirls_{act}",
            extra={"performer_id": pid, "product": "camgirls"},
        )
    except Exception:
        pass

    if act == "unlock":
        from backend.services.camgirls_service import grant_unlock_after_payment

        return grant_unlock_after_payment(uid, pid, payment_ref=order_id, provider="paypal")
    if act == "tip":
        from backend.services.camgirls_service import tip_performer_after_payment

        return tip_performer_after_payment(
            uid, pid, float(pending.get("amount_mn2") or 1), payment_ref=order_id, provider="paypal"
        )
    if act == "gift":
        from backend.services.camgirls_studio_service import gift_after_payment

        return gift_after_payment(
            uid, pid, gift_id=pending.get("gift_id"), payment_ref=order_id, provider="paypal"
        )
    return {"success": False, "error": "unhandled_action"}
