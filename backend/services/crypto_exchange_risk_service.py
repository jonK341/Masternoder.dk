"""Risk limits for exchange fiat on-ramps (daily/monthly caps, velocity, geo)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex


def _limits() -> Dict[str, Any]:
    cfg = ex.load_config()
    limits = cfg.get("risk_limits")
    return limits if isinstance(limits, dict) else {}


def _captured_fiat_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in (ex._PAYPAL_CRYPTO_ORDERS_PATH, ex._PAYPAL_MN2_ORDERS_PATH):
        data = ex._read_json(path, {})
        captured = data.get("captured") if isinstance(data, dict) else {}
        for row in (captured or {}).values():
            if not isinstance(row, dict):
                continue
            rows.append({
                "user_id": str(row.get("user_id") or ""),
                "ts": row.get("captured_at"),
                "usd": float(row.get("usd_amount") or row.get("amount_usd") or 0),
            })
    return rows


def _pending_and_captured_rows() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in (ex._PAYPAL_CRYPTO_ORDERS_PATH, ex._PAYPAL_MN2_ORDERS_PATH):
        data = ex._read_json(path, {})
        if not isinstance(data, dict):
            continue
        for bucket in ("pending", "captured"):
            for row in (data.get(bucket) or {}).values():
                if not isinstance(row, dict):
                    continue
                quote = row.get("quote") if isinstance(row.get("quote"), dict) else {}
                user_id = row.get("user_id") or quote.get("user_id")
                ts = row.get("captured_at") or row.get("created_at")
                rows.append({"user_id": str(user_id or ""), "ts": ts})
    return rows


def _sum_usd_since(user_id: str, since: datetime) -> float:
    total = 0.0
    for row in _captured_fiat_rows():
        if row["user_id"] != user_id:
            continue
        ts = ex._parse_iso(row.get("ts"))
        if ts and ts >= since:
            total += float(row.get("usd") or 0)
    return round(total, 2)


def _count_buys_since(user_id: str, since: datetime) -> int:
    count = 0
    for row in _pending_and_captured_rows():
        if row["user_id"] != user_id:
            continue
        ts = ex._parse_iso(row.get("ts"))
        if ts and ts >= since:
            count += 1
    return count


def _open_order_count(user_id: str) -> int:
    return sum(
        1 for o in ex._read_orders()
        if o.get("user_id") == user_id and o.get("status") == "open"
    )


def check_fiat_buy(user_id: str, usd_amount: float, *, country: Optional[str] = None) -> Dict[str, Any]:
    """Return {"ok": bool, ...}. Enforces caps/velocity/geo for fiat on-ramps."""
    limits = _limits()
    uid = str(user_id or "").strip()
    usd = float(usd_amount or 0)
    if not limits.get("enabled", True):
        return {"ok": True, "review": usd >= float(limits.get("review_threshold_usd") or 1e12)}
    if not uid or uid.lower() == "default_user":
        return {"ok": False, "error": "account_required"}

    geo = (country or "").strip().upper()
    blocked = [str(c).upper() for c in (limits.get("blocked_countries") or [])]
    if geo and geo in blocked:
        return {"ok": False, "error": "country_blocked", "country": geo}

    now = datetime.now(timezone.utc)
    day_cap = float(limits.get("daily_fiat_buy_usd_cap") or 0)
    month_cap = float(limits.get("monthly_fiat_buy_usd_cap") or 0)
    spent_day = _sum_usd_since(uid, now - timedelta(days=1))
    spent_month = _sum_usd_since(uid, now - timedelta(days=30))

    if day_cap > 0 and (spent_day + usd) > day_cap:
        return {"ok": False, "error": "daily_cap_exceeded", "cap_usd": day_cap, "spent_usd": spent_day, "remaining_usd": round(max(0.0, day_cap - spent_day), 2)}
    if month_cap > 0 and (spent_month + usd) > month_cap:
        return {"ok": False, "error": "monthly_cap_exceeded", "cap_usd": month_cap, "spent_usd": spent_month, "remaining_usd": round(max(0.0, month_cap - spent_month), 2)}

    velocity = int(limits.get("velocity_max_buys_per_hour") or 0)
    if velocity > 0 and _count_buys_since(uid, now - timedelta(hours=1)) >= velocity:
        return {"ok": False, "error": "velocity_exceeded", "max_per_hour": velocity}

    review = usd >= float(limits.get("review_threshold_usd") or 1e12)
    return {
        "ok": True,
        "review": review,
        "spent_day_usd": spent_day,
        "spent_month_usd": spent_month,
        "daily_remaining_usd": round(max(0.0, day_cap - spent_day - usd), 2) if day_cap > 0 else None,
    }


def user_risk_snapshot(user_id: str) -> Dict[str, Any]:
    limits = _limits()
    uid = str(user_id or "").strip()
    now = datetime.now(timezone.utc)
    return {
        "success": True,
        "user_id": uid,
        "spent_day_usd": _sum_usd_since(uid, now - timedelta(days=1)),
        "spent_month_usd": _sum_usd_since(uid, now - timedelta(days=30)),
        "buys_last_hour": _count_buys_since(uid, now - timedelta(hours=1)),
        "open_orders": _open_order_count(uid),
        "limits": limits,
    }
