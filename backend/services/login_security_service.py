"""
Login security — rate limiting, failed-attempt tracking, optional password gate.
"""
import json
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ATTEMPTS_PATH = os.path.join(_BASE_DIR, "data", "login_attempts.json")
_lock = threading.Lock()

_MAX_ATTEMPTS = 8
_LOCKOUT_MINUTES = 15
_WINDOW_MINUTES = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_attempts() -> Dict[str, Any]:
    if not os.path.exists(_ATTEMPTS_PATH):
        return {"ips": {}, "users": {}}
    try:
        with open(_ATTEMPTS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"ips": {}, "users": {}}


def _save_attempts(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_ATTEMPTS_PATH), exist_ok=True)
    with open(_ATTEMPTS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _prune_entries(entries: dict, cutoff: datetime) -> dict:
    kept = {}
    for key, rec in (entries or {}).items():
        if not isinstance(rec, dict):
            continue
        locked_until = rec.get("locked_until")
        if locked_until:
            try:
                if datetime.fromisoformat(locked_until.replace("Z", "+00:00")) > cutoff:
                    kept[key] = rec
                    continue
            except Exception:
                pass
        fails = []
        for ts in rec.get("failures") or []:
            try:
                if datetime.fromisoformat(str(ts).replace("Z", "+00:00")) > cutoff:
                    fails.append(ts)
            except Exception:
                pass
        if fails or rec.get("locked_until"):
            rec = dict(rec)
            rec["failures"] = fails
            kept[key] = rec
    return kept


def _is_locked(rec: dict) -> Optional[str]:
    locked_until = rec.get("locked_until")
    if not locked_until:
        return None
    try:
        until = datetime.fromisoformat(locked_until.replace("Z", "+00:00"))
        if until > _utcnow():
            return locked_until
    except Exception:
        pass
    return None


def check_login_allowed(ip: str, user_id: str) -> Tuple[bool, Optional[str]]:
    """Return (allowed, error_message)."""
    cutoff = _utcnow() - timedelta(minutes=_WINDOW_MINUTES)
    with _lock:
        data = _load_attempts()
        data["ips"] = _prune_entries(data.get("ips") or {}, cutoff)
        data["users"] = _prune_entries(data.get("users") or {}, cutoff)
        for bucket, key in (("ips", ip or "unknown"), ("users", user_id or "")):
            if not key:
                continue
            rec = (data.get(bucket) or {}).get(key) or {}
            locked = _is_locked(rec)
            if locked:
                return False, f"Too many failed login attempts. Try again after {locked[:16]} UTC."
        return True, None


def record_login_failure(ip: str, user_id: str) -> None:
    now = _utcnow().isoformat()
    with _lock:
        data = _load_attempts()
        for bucket, key in (("ips", ip or "unknown"), ("users", user_id or "")):
            if not key:
                continue
            entries = data.setdefault(bucket, {})
            rec = entries.get(key) or {"failures": []}
            fails = list(rec.get("failures") or [])
            fails.append(now)
            cutoff = _utcnow() - timedelta(minutes=_WINDOW_MINUTES)
            fails = [f for f in fails if datetime.fromisoformat(f.replace("Z", "+00:00")) > cutoff]
            rec["failures"] = fails
            if len(fails) >= _MAX_ATTEMPTS:
                rec["locked_until"] = (_utcnow() + timedelta(minutes=_LOCKOUT_MINUTES)).isoformat()
            entries[key] = rec
        _save_attempts(data)


def record_login_success(ip: str, user_id: str) -> None:
    with _lock:
        data = _load_attempts()
        for bucket, key in (("ips", ip or "unknown"), ("users", user_id or "")):
            if not key:
                continue
            entries = data.get(bucket) or {}
            if key in entries:
                entries[key] = {"failures": [], "last_success": _utcnow().isoformat()}
        _save_attempts(data)


def login_requires_password(user_id: str) -> bool:
    """True when account has a password and password-on-login is enabled."""
    try:
        from backend.services.password_protection_service import get_password_status
        from backend.services.account_security_service import get_security_settings

        status = get_password_status(user_id)
        if not status.get("has_password"):
            return False
        settings = get_security_settings(user_id)
        return bool(settings.get("require_password_login", True))
    except Exception:
        return False
