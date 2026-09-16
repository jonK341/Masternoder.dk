"""
Metered white-label Generator API keys (#3 / C7).

Keys map to org_label + user_id + tier; usage is quota-enforced per subscription period.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

_LOCK = threading.Lock()
_RATE_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KEYS_PATH = os.path.join(_BASE, "data", "generator_api_keys.json")
_RATE_BUCKETS: Dict[str, List[float]] = {}


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_KEYS_PATH):
        return {"keys": [], "subscriptions": []}
    try:
        with open(_KEYS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"keys": [], "subscriptions": []}
        if not isinstance(data.get("keys"), list):
            data["keys"] = []
        if not isinstance(data.get("subscriptions"), list):
            data["subscriptions"] = []
        return data
    except Exception:
        return {"keys": [], "subscriptions": []}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_KEYS_PATH), exist_ok=True)
    with _LOCK:
        tmp = _KEYS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _KEYS_PATH)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _period_start(now: Optional[datetime] = None) -> datetime:
    now = now or _now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _tiers_config() -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.monetization_config_service import get_generator_api_tiers

        tiers = get_generator_api_tiers()
        return tiers if isinstance(tiers, dict) else {}
    except Exception:
        return {}


def get_tier(tier_id: str) -> Optional[Dict[str, Any]]:
    tid = (tier_id or "").strip()
    row = _tiers_config().get(tid)
    return dict(row) if isinstance(row, dict) else None


def tier_for_sku(sku_id: str) -> Optional[str]:
    sid = (sku_id or "").strip()
    for tid, row in _tiers_config().items():
        if not isinstance(row, dict):
            continue
        if (row.get("sku_id") or "") == sid or tid == sid:
            return tid
    try:
        from backend.services.monetization_config_service import get_digital_goods

        for good in get_digital_goods():
            if not isinstance(good, dict):
                continue
            if (good.get("id") or "") == sid and good.get("delivery") == "generator_api_tier":
                return (good.get("generator_api_tier") or "").strip() or None
    except Exception:
        pass
    return None


def list_public_tiers() -> Dict[str, Any]:
    tiers = []
    for tid, row in sorted(_tiers_config().items()):
        if not isinstance(row, dict):
            continue
        tiers.append({
            "id": tid,
            "name": row.get("name") or tid,
            "monthly_jobs": int(row.get("monthly_jobs") or 0),
            "rate_limit_per_minute": int(row.get("rate_limit_per_minute") or 0),
            "max_duration_sec": int(row.get("max_duration_sec") or 180),
            "max_keys": int(row.get("max_keys") or 1),
            "subscription_days": int(row.get("subscription_days") or 30),
            "price_usd": float(row.get("price_usd") or 0),
            "price_coins": int(row.get("price_coins") or 0),
            "sku_id": row.get("sku_id"),
        })
    return {"success": True, "tiers": tiers, "auth_header": "X-Generator-Api-Key"}


def _active_subscriptions(user_id: str, *, tier_id: Optional[str] = None) -> List[Dict[str, Any]]:
    uid = (user_id or "").strip()
    now = _now()
    out = []
    for sub in _load().get("subscriptions") or []:
        if not isinstance(sub, dict):
            continue
        if (sub.get("user_id") or "") != uid:
            continue
        if tier_id and (sub.get("tier_id") or "") != tier_id:
            continue
        exp = _parse_dt(sub.get("expires_at"))
        if exp and exp < now:
            continue
        out.append(sub)
    return out


def _subscription_for_key(key_row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sid = (key_row.get("subscription_id") or "").strip()
    if sid:
        for sub in _load().get("subscriptions") or []:
            if isinstance(sub, dict) and (sub.get("id") or "") == sid:
                exp = _parse_dt(sub.get("expires_at"))
                if exp and exp < _now():
                    return None
                return sub
    uid = (key_row.get("user_id") or "").strip()
    tid = (key_row.get("tier_id") or "").strip()
    subs = _active_subscriptions(uid, tier_id=tid or None)
    return subs[0] if subs else None


def _ensure_period(sub: Dict[str, Any]) -> Dict[str, Any]:
    ps = _parse_dt(sub.get("period_start"))
    now = _now()
    start = _period_start(now)
    if not ps or ps < start:
        sub = dict(sub)
        sub["period_start"] = start.isoformat()
        sub["jobs_used"] = 0
    return sub


def grant_tier_subscription(
    user_id: str,
    tier_id: str,
    *,
    days: Optional[int] = None,
    source: str = "shop",
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    tid = (tier_id or "").strip()
    tier = get_tier(tid)
    if not uid or not tier:
        return {"success": False, "error": "invalid_tier_or_user"}
    span = int(days if days is not None else tier.get("subscription_days") or 30)
    now = _now()
    data = _load()
    subs = data.get("subscriptions") if isinstance(data.get("subscriptions"), list) else []
    existing = None
    for sub in subs:
        if isinstance(sub, dict) and sub.get("user_id") == uid and sub.get("tier_id") == tid:
            exp = _parse_dt(sub.get("expires_at"))
            if exp and exp >= now:
                existing = sub
                break
    if existing:
        exp = _parse_dt(existing.get("expires_at")) or now
        base = exp if exp > now else now
        existing["expires_at"] = (base + timedelta(days=span)).isoformat()
        existing["source"] = source
        row = existing
    else:
        row = {
            "id": secrets.token_hex(8),
            "user_id": uid,
            "tier_id": tid,
            "expires_at": (now + timedelta(days=span)).isoformat(),
            "jobs_used": 0,
            "period_start": _period_start(now).isoformat(),
            "source": source,
            "created_at": now.isoformat(),
        }
        subs.append(row)
    data["subscriptions"] = subs[-2000:]
    _save(data)
    return {
        "success": True,
        "subscription_id": row.get("id"),
        "tier_id": tid,
        "expires_at": row.get("expires_at"),
        "extended": existing is not None,
    }


def purchase_tier_coins(user_id: str, tier_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    tier = get_tier(tier_id)
    if not uid or not tier:
        return {"success": False, "error": "invalid_tier_or_user"}
    price = int(tier.get("price_coins") or 0)
    if price <= 0:
        return {"success": False, "error": "tier_not_coin_purchasable"}
    try:
        from backend.services.unified_points_database import unified_points_db

        bal = unified_points_db.get_all_points(uid)
        coins = int((bal.get("points") or {}).get("coins") or 0)
        if coins < price:
            return {"success": False, "error": "insufficient_coins", "price_coins": price, "balance_coins": coins}
        unified_points_db.add_points(
            user_id=uid,
            point_type="coins",
            amount=-price,
            source="generator_api_tier",
            metadata={"tier_id": tier_id},
        )
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    out = grant_tier_subscription(uid, tier_id, source="shop_coins")
    out["price_paid_coins"] = price
    return out


def get_user_api_status(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id_required"}
    subs_out = []
    for sub in _active_subscriptions(uid):
        sub = _ensure_period(sub)
        tier = get_tier(sub.get("tier_id") or "") or {}
        monthly = int(tier.get("monthly_jobs") or 0)
        used = int(sub.get("jobs_used") or 0)
        subs_out.append({
            "subscription_id": sub.get("id"),
            "tier_id": sub.get("tier_id"),
            "tier_name": tier.get("name"),
            "expires_at": sub.get("expires_at"),
            "jobs_used": used,
            "jobs_remaining": max(0, monthly - used),
            "monthly_jobs": monthly,
            "max_keys": int(tier.get("max_keys") or 1),
        })
    keys_out = []
    for row in _load().get("keys") or []:
        if not isinstance(row, dict) or (row.get("user_id") or "") != uid:
            continue
        keys_out.append({
            "id": row.get("id"),
            "label": row.get("label"),
            "org_label": row.get("org_label"),
            "tier_id": row.get("tier_id"),
            "created_at": row.get("created_at"),
            "active": row.get("active"),
        })
    return {"success": True, "user_id": uid, "subscriptions": subs_out, "keys": keys_out}


def _count_user_keys(user_id: str, tier_id: str) -> int:
    n = 0
    for row in _load().get("keys") or []:
        if not isinstance(row, dict) or not row.get("active"):
            continue
        if (row.get("user_id") or "") == user_id and (row.get("tier_id") or "") == tier_id:
            n += 1
    return n


def create_api_key(
    *,
    org_label: str,
    user_id: str,
    label: Optional[str] = None,
    tier_id: Optional[str] = None,
    subscription_id: Optional[str] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    tid = (tier_id or "").strip() or None
    sub_row = None
    if tid:
        subs = _active_subscriptions(uid, tier_id=tid)
        if subscription_id:
            subs = [s for s in subs if (s.get("id") or "") == subscription_id] or subs
        if not subs:
            return {"success": False, "error": "no_active_subscription", "tier_id": tid}
        sub_row = subs[0]
        tier = get_tier(tid) or {}
        max_keys = int(tier.get("max_keys") or 1)
        if _count_user_keys(uid, tid) >= max_keys:
            return {"success": False, "error": "max_keys_reached", "max_keys": max_keys}
    secret = os.environ.get("GENERATOR_API_KEY_SECRET") or "dev-change-me"
    raw = f"mn2gen_{secrets.token_urlsafe(24)}"
    h = _hash_key(f"{secret}:{raw}")
    row = {
        "id": secrets.token_hex(8),
        "key_hash": h,
        "org_label": (org_label or "").strip()[:256],
        "user_id": uid,
        "label": (label or org_label or "api")[:128],
        "tier_id": tid,
        "subscription_id": (sub_row.get("id") if sub_row else subscription_id) or None,
        "created_at": _now().isoformat(),
        "active": True,
    }
    data = _load()
    keys = data.get("keys") if isinstance(data.get("keys"), list) else []
    keys.append(row)
    data["keys"] = keys[-500:]
    _save(data)
    out = {
        "success": True,
        "api_key": raw,
        "key_id": row["id"],
        "org_label": row["org_label"],
        "tier_id": tid,
        "note": "Store api_key now — shown once.",
    }
    return out


def resolve_api_key(raw_key: str) -> Optional[Dict[str, Any]]:
    secret = os.environ.get("GENERATOR_API_KEY_SECRET") or "dev-change-me"
    h = _hash_key(f"{secret}:{(raw_key or '').strip()}")
    for row in _load().get("keys") or []:
        if not isinstance(row, dict) or not row.get("active"):
            continue
        if row.get("key_hash") == h:
            return row
    return None


def authenticate_request(headers: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    raw = (headers.get("X-Generator-Api-Key") or headers.get("Authorization") or "").strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw:
        return None, None
    row = resolve_api_key(raw)
    if not row:
        return None, "invalid_api_key"
    return row, None


def _rate_limit_ok(key_id: str, limit_per_minute: int) -> bool:
    if limit_per_minute <= 0:
        return True
    now = _now().timestamp()
    cutoff = now - 60.0
    with _RATE_LOCK:
        bucket = _RATE_BUCKETS.setdefault(key_id, [])
        bucket[:] = [t for t in bucket if t >= cutoff]
        if len(bucket) >= limit_per_minute:
            return False
        bucket.append(now)
    return True


def check_api_quota(key_row: Dict[str, Any], *, duration_sec: int = 0) -> Dict[str, Any]:
    if not key_row:
        return {"success": False, "error": "invalid_api_key"}
    tid = (key_row.get("tier_id") or "").strip()
    if not tid:
        return {"success": True, "unmetered": True}
    tier = get_tier(tid) or {}
    sub = _subscription_for_key(key_row)
    if not sub:
        return {"success": False, "error": "subscription_expired", "tier_id": tid}
    sub = _ensure_period(sub)
    monthly = int(tier.get("monthly_jobs") or 0)
    used = int(sub.get("jobs_used") or 0)
    remaining = max(0, monthly - used)
    max_dur = int(tier.get("max_duration_sec") or 300)
    if duration_sec and duration_sec > max_dur:
        return {
            "success": False,
            "error": "duration_exceeds_tier",
            "max_duration_sec": max_dur,
            "tier_id": tid,
        }
    if remaining <= 0:
        return {
            "success": False,
            "error": "monthly_quota_exceeded",
            "jobs_used": used,
            "monthly_jobs": monthly,
            "tier_id": tid,
        }
    rpm = int(tier.get("rate_limit_per_minute") or 0)
    kid = (key_row.get("id") or "").strip()
    if kid and not _rate_limit_ok(kid, rpm):
        return {"success": False, "error": "rate_limit_exceeded", "rate_limit_per_minute": rpm}
    return {
        "success": True,
        "jobs_remaining": remaining,
        "monthly_jobs": monthly,
        "tier_id": tid,
        "max_duration_sec": max_dur,
    }


def _persist_subscription(sub: Dict[str, Any]) -> None:
    data = _load()
    subs = data.get("subscriptions") if isinstance(data.get("subscriptions"), list) else []
    sid = (sub.get("id") or "").strip()
    for i, row in enumerate(subs):
        if isinstance(row, dict) and (row.get("id") or "") == sid:
            subs[i] = sub
            data["subscriptions"] = subs
            _save(data)
            return


def record_api_usage(
    key_row: Dict[str, Any],
    *,
    job_id: Optional[str] = None,
    duration_sec: int = 0,
) -> None:
    if not key_row:
        return
    tid = (key_row.get("tier_id") or "").strip()
    sub = _subscription_for_key(key_row)
    if not sub:
        return
    sub = _ensure_period(sub)
    sub["jobs_used"] = int(sub.get("jobs_used") or 0) + 1
    _persist_subscription(sub)
    try:
        from backend.services.cogs_metering_service import append_cogs_log

        append_cogs_log({
            "source": "generator_api",
            "user_id": key_row.get("user_id"),
            "org_label": key_row.get("org_label"),
            "tier_id": tid,
            "job_id": job_id,
            "duration_sec": duration_sec,
        })
    except Exception:
        pass


def list_keys_for_org(org_label: str) -> Dict[str, Any]:
    ol = (org_label or "").strip()
    out = []
    for row in _load().get("keys") or []:
        if isinstance(row, dict) and (row.get("org_label") or "") == ol:
            out.append({
                "id": row.get("id"),
                "label": row.get("label"),
                "user_id": row.get("user_id"),
                "tier_id": row.get("tier_id"),
                "created_at": row.get("created_at"),
                "active": row.get("active"),
            })
    return {"success": True, "org_label": ol, "keys": out}