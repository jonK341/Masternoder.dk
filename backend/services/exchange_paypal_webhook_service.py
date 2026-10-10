"""Exchange-side PayPal webhook handler.

Listens for PAYMENT.CAPTURE.COMPLETED events and fulfills pending exchange
orders (crypto buys and MN2 packs) without requiring the user to be online.

Idempotency: if the order was already captured the fulfill functions return
``{"success": True, "duplicate": True, ...}`` — we treat that as success and
return HTTP 200 so PayPal stops retrying.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Tuple

from backend.services import crypto_exchange_service as ex


# ── helpers ─────────────────────────────────────────────────────────────────

def _lookup_order(order_id: str) -> Tuple[str, Dict[str, Any]]:
    """Return (order_type, pending_row) for *order_id* or raise KeyError."""
    crypto = ex._read_json(ex._PAYPAL_CRYPTO_ORDERS_PATH, {"pending": {}})
    row = (crypto.get("pending") or {}).get(order_id)
    if row:
        return "crypto", row

    mn2 = ex._read_json(ex._PAYPAL_MN2_ORDERS_PATH, {"pending": {}})
    row = (mn2.get("pending") or {}).get(order_id)
    if row:
        return "mn2", row

    # Also check already-captured (idempotency)
    if order_id in (crypto.get("captured") or {}):
        return "crypto_dup", crypto["captured"][order_id]
    if order_id in (mn2.get("captured") or {}):
        return "mn2_dup", mn2["captured"][order_id]

    raise KeyError(f"order_not_found:{order_id}")


def _build_capture(event: Dict[str, Any]) -> Dict[str, Any]:
    """Extract capture details from a PAYMENT.CAPTURE.COMPLETED event."""
    resource = event.get("resource") or {}
    capture_id = resource.get("id") or event.get("resource_id") or ""
    seller_amount = resource.get("seller_receivable_breakdown") or {}
    amount_obj = resource.get("amount") or {}
    gross = seller_amount.get("gross_amount") or amount_obj
    return {
        "success": True,
        "capture_id": capture_id,
        "amount": float((gross.get("value") or 0) if isinstance(gross, dict) else 0),
        "currency": (gross.get("currency_code") or "USD") if isinstance(gross, dict) else "USD",
        "status": (resource.get("status") or "COMPLETED").upper(),
    }


# ── main handler ─────────────────────────────────────────────────────────────

def handle_webhook_event(event: Dict[str, Any]) -> Dict[str, Any]:
    """Process one PayPal webhook event dict and return a result dict.

    Always returns ``{"success": …}``; callers respond HTTP 200 regardless so
    PayPal stops retrying on application-level errors.
    """
    event_type = (event.get("event_type") or "").upper()

    if event_type not in ("PAYMENT.CAPTURE.COMPLETED", "CHECKOUT.ORDER.APPROVED"):
        return {"success": True, "skipped": True, "event_type": event_type}

    # Extract order_id — may live at resource.supplementary_data or resource.id
    resource = event.get("resource") or {}
    order_id = (
        ((resource.get("supplementary_data") or {}).get("related_ids") or {}).get("order_id")
        or resource.get("id")
        or ""
    ).strip()

    if not order_id:
        return {"success": False, "error": "no_order_id_in_event"}

    try:
        order_type, row = _lookup_order(order_id)
    except KeyError as exc:
        ex._audit("exchange_webhook_unknown_order", order_id=order_id, event_type=event_type)
        return {"success": False, "error": str(exc)}

    # Already captured — idempotent success
    if order_type.endswith("_dup"):
        return {"success": True, "duplicate": True, "order_id": order_id, "order_type": order_type}

    capture = _build_capture(event)
    user_id = str(row.get("user_id") or (row.get("quote") or {}).get("user_id") or "").strip()

    if not user_id:
        ex._audit("exchange_webhook_no_user", order_id=order_id)
        return {"success": False, "error": "no_user_id_for_order"}

    if order_type == "crypto":
        result = ex.fulfill_paypal_crypto_order(user_id, order_id, capture)
    else:
        result = ex.fulfill_paypal_mn2_order(user_id, order_id, capture)

    ex._audit(
        "exchange_webhook_fulfilled",
        order_id=order_id,
        order_type=order_type,
        user_id=user_id,
        success=result.get("success"),
        duplicate=result.get("duplicate"),
    )
    return {**result, "order_id": order_id, "order_type": order_type}


def process_paypal_webhook(headers: Any, body: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
    """Verify signature and dispatch.  Returns (response_dict, http_status)."""
    # Signature verification (bypass-able for local dev via PAYPAL_WEBHOOK_BYPASS=1)
    try:
        from backend.services.paypal_webhook_service import verify_paypal_webhook_signature
        if not verify_paypal_webhook_signature(headers, body):
            return {"success": False, "error": "invalid_webhook_signature"}, 400
    except Exception as exc:
        return {"success": False, "error": f"webhook_verify_error:{exc}"}, 500

    result = handle_webhook_event(body)
    return result, 200
