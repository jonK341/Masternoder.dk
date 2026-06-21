"""
Account security for real-money balances — settings, verification sessions, purchase/casino gates.
"""
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SETTINGS_PATH = os.path.join(_BASE_DIR, "data", "account_security_settings.json")
_VERIFY_TTL_MINUTES = 15


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_settings() -> Dict[str, Any]:
    if not os.path.exists(_SETTINGS_PATH):
        return {"users": {}, "defaults": {"security_preset": "balanced", "require_password_login": True, "require_password_real_money": True, "require_password_purchases": False, "require_password_bind_session": False}}
    try:
        with open(_SETTINGS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "defaults": {}}


def _save_settings(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_SETTINGS_PATH), exist_ok=True)
    with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _real_money_balances(user_id: str) -> Dict[str, float]:
    try:
        from backend.services.unified_points_database import unified_points_db

        pts = unified_points_db.get_all_points(user_id) or {}
        systems = pts.get("systems") or {}
        mn2 = float(pts.get("mn2_balance") or systems.get("mn2_balance") or 0)
        fiat = float(pts.get("casino_fiat_balance") or systems.get("casino_fiat_balance") or 0)
        return {"mn2_balance": mn2, "casino_fiat_balance": fiat, "has_real_money": mn2 > 0 or fiat > 0}
    except Exception:
        return {"mn2_balance": 0.0, "casino_fiat_balance": 0.0, "has_real_money": False}


def get_security_settings(user_id: str) -> Dict[str, Any]:
    data = _load_settings()
    defaults = data.get("defaults") or {}
    user = (data.get("users") or {}).get(user_id) or {}
    merged = {
        "security_preset": defaults.get("security_preset", "balanced"),
        "require_password_login": defaults.get("require_password_login", True),
        "require_password_real_money": defaults.get("require_password_real_money", True),
        "require_password_purchases": defaults.get("require_password_purchases", False),
        "require_password_bind_session": defaults.get("require_password_bind_session", False),
    }
    merged.update({k: v for k, v in user.items() if k.startswith("require_") or k == "security_preset"})
    return merged


SECURITY_PRESETS = {
    "balanced": {
        "require_password_login": False,
        "require_password_real_money": True,
        "require_password_purchases": False,
        "require_password_bind_session": False,
    },
    "secure": {
        "require_password_login": True,
        "require_password_real_money": True,
        "require_password_purchases": False,
        "require_password_bind_session": True,
    },
    "maximum": {
        "require_password_login": True,
        "require_password_real_money": True,
        "require_password_purchases": True,
        "require_password_bind_session": True,
    },
}


def apply_security_preset(preset: str) -> Dict[str, bool]:
    key = (preset or "balanced").strip().lower()
    return dict(SECURITY_PRESETS.get(key, SECURITY_PRESETS["balanced"]))


def bind_session_requires_password(user_id: str) -> bool:
    settings = get_security_settings(user_id)
    if settings.get("require_password_bind_session"):
        return True
    try:
        from backend.services.password_protection_service import get_password_status

        pwd = get_password_status(user_id)
        if pwd.get("has_password") and settings.get("security_preset") in ("secure", "maximum"):
            return True
    except Exception:
        pass
    return False


def update_security_settings(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    allowed = {
        "require_password_login",
        "require_password_real_money",
        "require_password_purchases",
        "require_password_bind_session",
        "security_preset",
    }
    clean: Dict[str, Any] = {}
    preset = (updates.get("security_preset") or "").strip().lower()
    if preset in SECURITY_PRESETS:
        clean["security_preset"] = preset
        for k, v in apply_security_preset(preset).items():
            clean[k] = bool(v)
    for k, v in updates.items():
        if k in allowed and k != "security_preset":
            clean[k] = bool(v) if k.startswith("require_") else v
    data = _load_settings()
    users = data.setdefault("users", {})
    row = dict(users.get(user_id) or {})
    row.update(clean)
    row["updated_at"] = _utcnow().isoformat()
    users[user_id] = row
    _save_settings(data)
    return {"success": True, "settings": get_security_settings(user_id)}


def get_security_status(user_id: str) -> Dict[str, Any]:
    from backend.services.password_protection_service import get_password_status

    pwd = get_password_status(user_id)
    balances = _real_money_balances(user_id)
    settings = get_security_settings(user_id)
    return {
        "success": True,
        "user_id": user_id,
        "has_password": bool(pwd.get("has_password")),
        "can_unlock_password": bool(pwd.get("can_unlock")),
        "has_real_money": balances["has_real_money"],
        "mn2_balance": balances["mn2_balance"],
        "casino_fiat_balance": balances["casino_fiat_balance"],
        "settings": settings,
        "recommendations": _recommendations(pwd, balances, settings),
    }


def _recommendations(pwd: dict, balances: dict, settings: dict) -> list:
    recs = []
    if balances.get("has_real_money") and not pwd.get("has_password"):
        recs.append("Set a password — you hold real-money balance (MN2 or casino USD).")
    if balances.get("has_real_money") and pwd.get("has_password") and not settings.get("require_password_real_money"):
        recs.append("Enable real-money protection to require password before MN2/USD casino bets.")
    if pwd.get("has_password") and not settings.get("require_password_login"):
        recs.append("Consider enabling password-on-login for this account.")
    if settings.get("security_preset") == "balanced" and balances.get("has_real_money"):
        recs.append("Switch security preset to Secure or Maximum — you hold real-money balance.")
    if not settings.get("require_password_bind_session") and pwd.get("has_password"):
        recs.append("Enable bind-session password so others cannot hijack your user ID in this browser.")
    return recs


def issue_verification_token(user_id: str, password: str) -> Dict[str, Any]:
    from backend.services.password_protection_service import verify_password

    result = verify_password(user_id, password)
    if not result.get("success"):
        return result
    token = secrets.token_urlsafe(24)
    expires = (_utcnow() + timedelta(minutes=_VERIFY_TTL_MINUTES)).isoformat()
    data = _load_settings()
    users = data.setdefault("users", {})
    row = dict(users.get(user_id) or {})
    row["verify_token"] = token
    row["verify_expires"] = expires
    users[user_id] = row
    _save_settings(data)
    return {
        "success": True,
        "verification_token": token,
        "expires_at": expires,
        "ttl_minutes": _VERIFY_TTL_MINUTES,
    }


def _token_valid(user_id: str, token: Optional[str]) -> bool:
    if not token:
        return False
    data = _load_settings()
    row = (data.get("users") or {}).get(user_id) or {}
    if row.get("verify_token") != token:
        return False
    expires = row.get("verify_expires")
    if not expires:
        return False
    try:
        return datetime.fromisoformat(expires.replace("Z", "+00:00")) > _utcnow()
    except Exception:
        return False


def verify_action_token(user_id: str, token: Optional[str]) -> bool:
    """Public check: is this a currently-valid password-verification token for the user?
    Used by risk-based step-up (it must enforce even when require_password_real_money is off)."""
    return _token_valid(user_id, token)


def has_password(user_id: str) -> bool:
    """True if the user has a password set (so step-up can demand a verification token)."""
    try:
        from backend.services.password_protection_service import get_password_status
        return bool(get_password_status(user_id).get("has_password"))
    except Exception:
        return False


def check_real_money_action(user_id: str, verification_token: Optional[str] = None) -> Optional[str]:
    """Return error message if action blocked, else None."""
    settings = get_security_settings(user_id)
    if not settings.get("require_password_real_money"):
        return None
    balances = _real_money_balances(user_id)
    if not balances.get("has_real_money"):
        return None
    try:
        from backend.services.password_protection_service import get_password_status

        if not get_password_status(user_id).get("has_password"):
            return "Set a password on your profile before using real-money casino balances."
    except Exception:
        return "Password verification required for real-money actions."
    if _token_valid(user_id, verification_token):
        return None
    return "Password verification required. Verify at /api/user/security/verify with your account password."


def check_purchase_action(user_id: str, verification_token: Optional[str] = None, price_usd: float = 0) -> Optional[str]:
    settings = get_security_settings(user_id)
    if not settings.get("require_password_purchases") or price_usd <= 0:
        return None
    try:
        from backend.services.password_protection_service import get_password_status

        if not get_password_status(user_id).get("has_password"):
            return "Set a password before enabling purchase protection."
    except Exception:
        return "Password verification required for purchases."
    if _token_valid(user_id, verification_token):
        return None
    return "Password verification required for this purchase."
