"""Admin exchange board — operational overview for the exchange."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List

from backend.services import crypto_exchange_service as ex


def _orders_summary(path: str) -> Dict[str, Any]:
    data = ex._read_json(path, {"pending": {}, "captured": {}})
    pending = data.get("pending") if isinstance(data.get("pending"), dict) else {}
    captured = data.get("captured") if isinstance(data.get("captured"), dict) else {}
    captured_usd = 0.0
    for row in captured.values():
        if isinstance(row, dict):
            captured_usd += float(row.get("usd_amount") or row.get("amount_usd") or 0)
    now = datetime.now(timezone.utc)
    stale = 0
    for row in pending.values():
        if not isinstance(row, dict):
            continue
        quote = row.get("quote") if isinstance(row.get("quote"), dict) else {}
        expires = ex._parse_iso(quote.get("expires_at") or row.get("expires_at"))
        if expires and expires < now:
            stale += 1
    return {
        "pending_count": len(pending),
        "captured_count": len(captured),
        "captured_usd": round(captured_usd, 2),
        "stale_pending_count": stale,
    }


def _recent_risk_denials(limit: int = 20) -> List[Dict[str, Any]]:
    tail = ex.get_audit_tail(limit=200).get("records") or []
    denials = [r for r in tail if r.get("action") == "risk_denied"]
    return denials[:limit]


def _trade_volume(since_hours: float = 24.0) -> Dict[str, Any]:
    trades = ex.list_trades(limit=200).get("trades") or []
    since = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    usd = 0.0
    count = 0
    for t in trades:
        ts = ex._parse_iso(t.get("ts"))
        if ts and ts >= since:
            count += 1
            usd += float(t.get("usd_value") or 0)
    return {"window_hours": since_hours, "trade_count": count, "usd_volume": round(usd, 2)}


def admin_board() -> Dict[str, Any]:
    crypto = _orders_summary(ex._PAYPAL_CRYPTO_ORDERS_PATH)
    mn2 = _orders_summary(ex._PAYPAL_MN2_ORDERS_PATH)
    treasury = ex._read_json(ex._TREASURY_PATH, {"total_fees_mn2": 0, "updated_at": None})
    audit = ex.verify_audit_chain()
    open_orders = [o for o in ex._read_orders() if o.get("status") == "open"]

    return {
        "success": True,
        "generated_at": ex._iso(),
        "fiat_orders": {
            "paypal_crypto": crypto,
            "paypal_mn2": mn2,
            "total_pending": crypto["pending_count"] + mn2["pending_count"],
            "total_captured_usd": round(crypto["captured_usd"] + mn2["captured_usd"], 2),
            "total_stale_pending": crypto["stale_pending_count"] + mn2["stale_pending_count"],
        },
        "open_limit_orders": len(open_orders),
        "treasury": {
            "total_fees_mn2": round(float(treasury.get("total_fees_mn2") or 0), 8),
            "total_fees_usd_est": round(float(treasury.get("total_fees_mn2") or 0) * ex._mn2_usd(), 2),
            "updated_at": treasury.get("updated_at"),
        },
        "trade_volume_24h": _trade_volume(24.0),
        "audit": audit,
        "risk_denials_recent": _recent_risk_denials(),
        "risk_limits": ex.load_config().get("risk_limits") or {},
    }
