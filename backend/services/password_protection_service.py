"""
Password protection service — encrypted (hashed) passwords as a reward for completing and earning points.
Users unlock the ability to set a password when they reach min_game_points or min_investigations; setting a password awards a small game_points reward.
"""
import os
import json
import hashlib
import secrets
from datetime import datetime
from datetime import timedelta
from typing import Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROTECTION_PATH = os.path.join(BASE_DIR, "data", "user_password_protection.json")
INVESTIGATIONS_PATH = os.path.join(BASE_DIR, "data", "star_map_25_investigations.json")


def _load_protection() -> Dict[str, Any]:
    if not os.path.exists(PROTECTION_PATH):
        return {"users": {}, "unlock_rule": {"min_game_points": 50, "min_investigations": 1}, "reward_on_set": {"game_points": 10}}
    try:
        with open(PROTECTION_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"users": {}, "unlock_rule": {"min_game_points": 50, "min_investigations": 1}, "reward_on_set": {"game_points": 10}}


def _save_protection(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(PROTECTION_PATH), exist_ok=True)
    with open(PROTECTION_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _hash_password(password: str) -> str:
    from werkzeug.security import generate_password_hash
    return generate_password_hash(password, method="pbkdf2:sha256", salt_length=16)


def _check_password(password_hash: str, password: str) -> bool:
    from werkzeug.security import check_password_hash
    return check_password_hash(password_hash, password)


def _user_game_points(user_id: str) -> float:
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(user_id) or {}
        return float(pts.get("game_points", 0) or pts.get("systems", {}).get("game_points", 0) or 0)
    except Exception:
        return 0.0


def _user_investigations_count(user_id: str) -> int:
    if not os.path.exists(INVESTIGATIONS_PATH):
        return 0
    try:
        with open(INVESTIGATIONS_PATH, "r", encoding="utf-8") as f:
            inv = json.load(f)
        return len(inv.get(user_id, []))
    except Exception:
        return 0


def can_unlock_password(user_id: str) -> bool:
    """True if user has met the unlock rule (min_game_points OR min_investigations)."""
    data = _load_protection()
    rule = data.get("unlock_rule", {})
    min_pts = int(rule.get("min_game_points", 50))
    min_inv = int(rule.get("min_investigations", 1))
    return _user_game_points(user_id) >= min_pts or _user_investigations_count(user_id) >= min_inv


def _real_money_account(user_id: str) -> bool:
    try:
        from backend.services.account_security_service import _real_money_balances

        return bool(_real_money_balances(user_id).get("has_real_money"))
    except Exception:
        return False


def _fast_track_reason(user_id: str) -> Optional[str]:
    """Accounts with verified identity or real-money balance can set a password immediately."""
    recovery = get_recovery_status(user_id)
    if recovery.get("has_email"):
        return "verified email on profile"
    if recovery.get("provider_recovery_supported"):
        provider = recovery.get("provider") or "social"
        return f"linked {provider} account"
    if _real_money_account(user_id):
        return "real-money balance (MN2 or casino USD)"
    return None


def get_unlock_progress(user_id: str) -> Dict[str, Any]:
    data = _load_protection()
    rule = data.get("unlock_rule", {})
    min_pts = int(rule.get("min_game_points", 50))
    min_inv = int(rule.get("min_investigations", 1))
    game_points = _user_game_points(user_id)
    investigations = _user_investigations_count(user_id)
    points_pct = min(100, int((game_points / min_pts) * 100)) if min_pts > 0 else 100
    inv_pct = min(100, int((investigations / min_inv) * 100)) if min_inv > 0 else 100
    primary_path = "investigations" if inv_pct >= points_pct else "game_points"
    return {
        "game_points": game_points,
        "min_game_points": min_pts,
        "game_points_percent": points_pct,
        "investigations": investigations,
        "min_investigations": min_inv,
        "investigations_percent": inv_pct,
        "overall_percent": max(points_pct, inv_pct),
        "primary_path": primary_path,
        "rule_met": can_unlock_password(user_id),
    }


def can_set_password(user_id: str) -> bool:
    """True when the account may set or change a password in the guided setup flow."""
    data = _load_protection()
    user = data.get("users", {}).get(user_id, {})
    if user.get("password_hash") or user.get("unlocked_at"):
        return True
    if can_unlock_password(user_id):
        return True
    return bool(_fast_track_reason(user_id))


def get_password_status(user_id: str) -> Dict[str, Any]:
    """Returns has_unlocked, has_password, can_unlock, unlock_rule, reward_on_set."""
    data = _load_protection()
    users = data.get("users", {})
    user = users.get(user_id, {})
    has_password = bool(user.get("password_hash"))
    unlocked_at = user.get("unlocked_at")
    has_unlocked = bool(unlocked_at) or has_password
    can_unlock = can_unlock_password(user_id)
    fast_track_reason = _fast_track_reason(user_id)
    return {
        "user_id": user_id,
        "has_unlocked": has_unlocked,
        "has_password": has_password,
        "can_unlock": can_unlock and not has_unlocked,
        "can_set_password": can_set_password(user_id),
        "fast_track": bool(fast_track_reason),
        "fast_track_reason": fast_track_reason,
        "unlock_progress": get_unlock_progress(user_id),
        "unlock_rule": data.get("unlock_rule", {}),
        "reward_on_set": data.get("reward_on_set", {}),
        "set_at": user.get("set_at"),
        "recovery": get_recovery_status(user_id),
    }


def _profile_preferences(user_id: str) -> Dict[str, Any]:
    try:
        from backend.services.user_onboarding import user_onboarding
        profile = user_onboarding.get_user_profile(user_id) or {}
        prefs = profile.get("preferences") or {}
        if isinstance(prefs, str):
            return json.loads(prefs) if prefs else {}
        return prefs if isinstance(prefs, dict) else {}
    except Exception:
        return {}


def _profile_email(user_id: str) -> Optional[str]:
    prefs = _profile_preferences(user_id)
    social = prefs.get("social_auth") if isinstance(prefs.get("social_auth"), dict) else {}
    email = (social.get("email") or prefs.get("email") or "").strip().lower()
    return email or None


def _linked_provider(user_id: str) -> Optional[str]:
    prefs = _profile_preferences(user_id)
    social = prefs.get("social_auth") if isinstance(prefs.get("social_auth"), dict) else {}
    provider = (social.get("provider") or "").strip().lower()
    return provider or None


def get_recovery_status(user_id: str) -> Dict[str, Any]:
    email = _profile_email(user_id)
    provider = _linked_provider(user_id)
    return {
        "has_email": bool(email),
        "email_masked": _mask_email(email) if email else None,
        "email_delivery_configured": _email_delivery_configured(),
        "provider": provider,
        "provider_recovery_supported": bool(provider),
        "token_reset_supported": True,
    }


def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    if not domain:
        return email
    return f"{name[:2]}***@{domain}"


def _email_delivery_configured() -> bool:
    return (os.getenv("PASSWORD_RECOVERY_EMAIL_ENABLED") or os.getenv("SMTP_HOST") or "").strip().lower() in {"1", "true", "yes", "on"} or bool(os.getenv("SMTP_HOST"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def request_password_recovery(user_id: str, email: Optional[str] = None) -> Dict[str, Any]:
    """Create a short-lived reset token when the account has a matching email or linked provider."""
    recovery = get_recovery_status(user_id)
    account_email = _profile_email(user_id)
    if email and account_email and email.strip().lower() != account_email:
        return {"success": False, "error": "Email does not match this account"}
    if not account_email and not recovery.get("provider_recovery_supported"):
        return {"success": False, "error": "No email or linked provider is available for recovery"}

    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(minutes=30)).isoformat() + "Z"
    data = _load_protection()
    users = data.setdefault("users", {})
    user = users.setdefault(user_id, {})
    user["recovery"] = {
        "token_hash": _hash_token(token),
        "requested_at": datetime.utcnow().isoformat() + "Z",
        "expires_at": expires_at,
        "email": account_email,
        "provider": recovery.get("provider"),
        "used_at": None,
    }
    _save_protection(data)
    result = {
        "success": True,
        "user_id": user_id,
        "expires_at": expires_at,
        "email_masked": recovery.get("email_masked"),
        "email_delivery_configured": recovery.get("email_delivery_configured"),
        "provider": recovery.get("provider"),
        "message": "Recovery token created. Email delivery is configured." if recovery.get("email_delivery_configured") else "Recovery token created. Configure email delivery to send reset links automatically.",
    }
    if not recovery.get("email_delivery_configured") or (os.getenv("PASSWORD_RECOVERY_RETURN_TOKEN") or "").strip().lower() in {"1", "true", "yes", "on"}:
        result["reset_token"] = token
    return result


def reset_password_with_recovery(user_id: str, token: str, new_password: str) -> Dict[str, Any]:
    if not (new_password and len(new_password) >= 6):
        return {"success": False, "error": "Password must be at least 6 characters"}
    data = _load_protection()
    user = data.get("users", {}).get(user_id, {})
    recovery = user.get("recovery") if isinstance(user.get("recovery"), dict) else {}
    if not recovery or recovery.get("used_at"):
        return {"success": False, "error": "No active recovery request"}
    expires_raw = recovery.get("expires_at") or ""
    try:
        expires_at = datetime.fromisoformat(expires_raw.replace("Z", ""))
        if expires_at < datetime.utcnow():
            return {"success": False, "error": "Recovery token expired"}
    except Exception:
        return {"success": False, "error": "Invalid recovery token state"}
    if recovery.get("token_hash") != _hash_token(token or ""):
        return {"success": False, "error": "Invalid recovery token"}
    users = data.setdefault("users", {})
    users.setdefault(user_id, {})
    users[user_id]["password_hash"] = _hash_password(new_password)
    users[user_id]["set_at"] = datetime.utcnow().isoformat() + "Z"
    users[user_id]["unlocked_at"] = users[user_id].get("unlocked_at") or datetime.utcnow().isoformat() + "Z"
    users[user_id]["recovery"]["used_at"] = datetime.utcnow().isoformat() + "Z"
    _save_protection(data)
    return {"success": True, "user_id": user_id, "message": "Password reset. Account protected."}


def unlock_password_protection(user_id: str) -> Dict[str, Any]:
    """If user meets unlock rule, mark as unlocked and return success. Does not set a password."""
    if not can_unlock_password(user_id):
        return {"success": False, "error": "Unlock requirement not met (earn points or complete investigations)"}
    data = _load_protection()
    users = data.get("users", {})
    if user_id not in users:
        users[user_id] = {}
    if users[user_id].get("unlocked_at"):
        return {"success": True, "already_unlocked": True, "user_id": user_id}
    users[user_id]["unlocked_at"] = datetime.utcnow().isoformat() + "Z"
    data["users"] = users
    _save_protection(data)
    return {"success": True, "unlocked": True, "user_id": user_id}


def set_password(user_id: str, new_password: str, current_password: Optional[str] = None) -> Dict[str, Any]:
    """Set or change password. User must be eligible (unlock rule, fast track, or already unlocked). Awards reward_on_set game_points once."""
    if not (new_password and len(new_password) >= 6):
        return {"success": False, "error": "Password must be at least 6 characters"}
    data = _load_protection()
    users = data.get("users", {})
    if user_id not in users:
        users[user_id] = {}
    existing_hash = users[user_id].get("password_hash")
    if existing_hash:
        if not current_password:
            return {"success": False, "error": "Current password required to change your password."}
        if not _check_password(existing_hash, current_password):
            return {"success": False, "error": "Current password is incorrect."}
    if not users[user_id].get("unlocked_at"):
        if not can_set_password(user_id):
            progress = get_unlock_progress(user_id)
            return {
                "success": False,
                "error": "Unlock requirement not met. Earn points or complete Star Map investigations.",
                "unlock_progress": progress,
            }
        unlock_password_protection(user_id)
        data = _load_protection()
        users = data.get("users", {})
        if user_id not in users:
            users[user_id] = {}
    users[user_id]["password_hash"] = _hash_password(new_password)
    users[user_id]["set_at"] = datetime.utcnow().isoformat() + "Z"
    reward = data.get("reward_on_set", {})
    points_awarded = 0
    if reward.get("game_points") and not users[user_id].get("reward_given"):
        try:
            from backend.services.unified_points_database import unified_points_db
            amt = int(reward.get("game_points", 10))
            unified_points_db.add_points(user_id, "game_points", amt, "password_protection_reward", {"message": reward.get("message", "Password set reward")})
            points_awarded = amt
            users[user_id]["reward_given"] = True
        except Exception:
            pass
    data["users"] = users
    _save_protection(data)
    return {"success": True, "user_id": user_id, "points_awarded": points_awarded, "message": "Password set. Account protected."}


def verify_password(user_id: str, password: str) -> Dict[str, Any]:
    """Verify password for sensitive actions. Returns success and optional token/session hint."""
    data = _load_protection()
    user = data.get("users", {}).get(user_id, {})
    stored = user.get("password_hash")
    if not stored:
        return {"success": False, "error": "No password set"}
    if not _check_password(stored, password):
        return {"success": False, "error": "Invalid password"}
    return {"success": True, "user_id": user_id}
