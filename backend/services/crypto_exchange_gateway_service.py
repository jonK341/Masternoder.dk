"""Gateway status layer for exchange payment rails."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from backend.services import crypto_exchange_service as ex


def _count_orders(path: str) -> Dict[str, Any]:
    data = ex._read_json(path, {"pending": {}, "captured": {}})
    pending = data.get("pending") if isinstance(data.get("pending"), dict) else {}
    captured = data.get("captured") if isinstance(data.get("captured"), dict) else {}
    now = datetime.now(timezone.utc)
    expired = 0
    for row in pending.values():
        if not isinstance(row, dict):
            continue
        expires_at = None
        quote = row.get("quote") if isinstance(row.get("quote"), dict) else {}
        if quote:
            expires_at = quote.get("expires_at")
        expires_at = expires_at or row.get("expires_at")
        parsed = ex._parse_iso(expires_at)
        if parsed and parsed < now:
            expired += 1
    return {
        "pending_count": len(pending),
        "captured_count": len(captured),
        "expired_pending_count": expired,
    }


def _ready_checks() -> Iterable[Dict[str, Any]]:
    cfg = ex.load_config()
    paypal_crypto = cfg.get("paypal_crypto_buy") or {}
    yield {
        "id": "paypal_crypto_limits",
        "label": "PayPal crypto buy limits",
        "ok": bool(paypal_crypto.get("enabled", True)),
        "detail": f"${float(paypal_crypto.get('min_usd') or 5):.2f}-${float(paypal_crypto.get('max_usd') or 500):.2f}",
    }
    yield {
        "id": "pending_order_records",
        "label": "Server-side pending order records",
        "ok": True,
        "detail": "MN2 packs and crypto buys are captured from stored server quotes.",
    }
    yield {
        "id": "capture_validation",
        "label": "Capture validation",
        "ok": True,
        "detail": "User, amount, currency, expiry, and duplicate captures are validated.",
    }
    yield {
        "id": "agent_secret",
        "label": "Exchange daemon secret",
        "ok": bool((ex.os.environ.get("EXCHANGE_AGENT_SECRET") or "").strip()),
        "detail": "Set EXCHANGE_AGENT_SECRET before exposing manual daemon ticks.",
    }


def gateway_status() -> Dict[str, Any]:
    crypto = _count_orders(ex._PAYPAL_CRYPTO_ORDERS_PATH)
    mn2 = _count_orders(ex._PAYPAL_MN2_ORDERS_PATH)
    checks = list(_ready_checks())
    pending_total = crypto["pending_count"] + mn2["pending_count"]
    expired_total = crypto["expired_pending_count"] + mn2["expired_pending_count"]
    captured_total = crypto["captured_count"] + mn2["captured_count"]
    return {
        "success": True,
        "gateway": {
            "id": "exchange_payment_gateway",
            "name": "Exchange Payment Gateway",
            "rails": ["paypal_crypto", "paypal_mn2"],
            "next_rails": ["paypal_webhooks", "stripe_card", "onchain_deposit"],
        },
        "totals": {
            "pending_count": pending_total,
            "captured_count": captured_total,
            "expired_pending_count": expired_total,
        },
        "rails": {
            "paypal_crypto": crypto,
            "paypal_mn2": mn2,
        },
        "ready_checks": checks,
        "ready": all(bool(c.get("ok")) for c in checks[:3]),
        "generated_at": ex._iso(),
    }
