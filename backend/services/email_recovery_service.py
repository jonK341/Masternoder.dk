"""
Email verification, change-email confirmation, and optional recovery email.
Reuses NOTIFY_SMTP_* via purchase_notification_service._send_email when configured.
"""
import hashlib
import json
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_EMAIL_PATH = os.path.join(_BASE_DIR, "data", "user_email_recovery.json")
_TOKEN_TTL_MINUTES = 60
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load() -> Dict[str, Any]:
    if not os.path.exists(_EMAIL_PATH):
        return {"users": {}}
    try:
        with open(_EMAIL_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_EMAIL_PATH), exist_ok=True)
    with open(_EMAIL_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _index_email(data: Dict[str, Any], email: str, user_id: str) -> None:
    index = data.setdefault("email_index", {})
    if isinstance(index, dict):
        index[email] = user_id


def _scan_profile_files_for_email(email: str) -> Optional[str]:
    profiles_dir = os.path.join(_BASE_DIR, "logs", "user_profiles")
    if not os.path.isdir(profiles_dir):
        return None
    try:
        for name in os.listdir(profiles_dir):
            if not name.endswith(".json"):
                continue
            path = os.path.join(profiles_dir, name)
            with open(path, "r", encoding="utf-8") as f:
                profile = json.load(f)
            uid = profile.get("user_id") or name[:-5]
            prefs = profile.get("preferences") or {}
            if isinstance(prefs, str):
                try:
                    prefs = json.loads(prefs)
                except Exception:
                    prefs = {}
            social = prefs.get("social_auth") if isinstance(prefs.get("social_auth"), dict) else {}
            candidate = _normalize_email(social.get("email") or prefs.get("email") or "")
            if candidate == email:
                return str(uid)
    except Exception:
        return None
    return None


def _hash_token(token: str) -> str:
    return hashlib.sha256((token or "").encode("utf-8")).hexdigest()


def _normalize_email(email: str) -> Optional[str]:
    value = (email or "").strip().lower()
    if not value or not _EMAIL_RE.match(value):
        return None
    return value


def _mask_email(email: str) -> str:
    name, _, domain = email.partition("@")
    if not domain:
        return email
    return f"{name[:2]}***@{domain}"


def _email_delivery_configured() -> bool:
    try:
        from backend.services.purchase_notification_service import SMTP_HOST, SMTP_USER, SMTP_PASSWORD
        return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)
    except Exception:
        return False


def _send_verification_email(to_email: str, subject: str, body: str) -> bool:
    try:
        from backend.services.purchase_notification_service import _send_email
        return _send_email(subject, body, to_email)
    except Exception:
        return False


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


def _profile_primary_email(user_id: str) -> Optional[str]:
    prefs = _profile_preferences(user_id)
    social = prefs.get("social_auth") if isinstance(prefs.get("social_auth"), dict) else {}
    email = _normalize_email(social.get("email") or prefs.get("email") or "")
    return email


def _set_profile_email(user_id: str, email: str, verified: bool = True) -> Dict[str, Any]:
    from backend.services.user_onboarding import user_onboarding

    profile = user_onboarding.get_user_profile(user_id)
    if not profile:
        created = user_onboarding.create_new_user(
            {"referral_source": "email_recovery", "preferences": {}},
            user_id,
        )
        if not created.get("success"):
            return created
        profile = user_onboarding.get_user_profile(user_id)

    prefs = _profile_preferences(user_id)
    prefs["email"] = email
    prefs["email_verified"] = verified
    prefs["email_updated_at"] = _utcnow().isoformat()
    return user_onboarding.update_user_profile(user_id, {"preferences": prefs})


def _user_row(user_id: str) -> Dict[str, Any]:
    data = _load()
    users = data.setdefault("users", {})
    row = users.get(user_id)
    if not isinstance(row, dict):
        row = {}
        users[user_id] = row
    return row


def _save_user_row(user_id: str, row: Dict[str, Any]) -> None:
    data = _load()
    data.setdefault("users", {})[user_id] = row
    _save(data)


def get_email_status(user_id: str) -> Dict[str, Any]:
    row = _user_row(user_id)
    primary = _profile_primary_email(user_id)
    recovery = row.get("recovery_email")
    return {
        "has_email": bool(primary),
        "email_masked": _mask_email(primary) if primary else None,
        "email_verified": bool(row.get("verified_at") or _profile_preferences(user_id).get("email_verified")),
        "recovery_email_masked": _mask_email(recovery) if recovery else None,
        "recovery_email_verified": bool(row.get("recovery_verified_at")),
        "pending_email_masked": _mask_email(row["pending_email"]) if row.get("pending_email") else None,
        "email_delivery_configured": _email_delivery_configured(),
        "verification_supported": True,
        "change_email_supported": True,
    }


def _issue_token(user_id: str, purpose: str, email: str) -> Dict[str, Any]:
    token = secrets.token_urlsafe(32)
    expires = (_utcnow() + timedelta(minutes=_TOKEN_TTL_MINUTES)).isoformat()
    row = _user_row(user_id)
    row["pending"] = {
        "purpose": purpose,
        "email": email,
        "token_hash": _hash_token(token),
        "expires_at": expires,
        "requested_at": _utcnow().isoformat(),
    }
    _save_user_row(user_id, row)
    return {"token": token, "expires_at": expires}


def _consume_token(user_id: str, token: str, purpose: str) -> Optional[str]:
    row = _user_row(user_id)
    pending = row.get("pending") if isinstance(row.get("pending"), dict) else {}
    if pending.get("purpose") != purpose:
        return None
    expires_raw = pending.get("expires_at") or ""
    try:
        if datetime.fromisoformat(expires_raw.replace("Z", "+00:00")) < _utcnow():
            return None
    except Exception:
        return None
    if pending.get("token_hash") != _hash_token(token or ""):
        return None
    email = pending.get("email")
    row.pop("pending", None)
    _save_user_row(user_id, row)
    return email if isinstance(email, str) else None


def request_email_verification(user_id: str, email: str) -> Dict[str, Any]:
    normalized = _normalize_email(email)
    if not normalized:
        return {"success": False, "error": "Valid email address required"}

    issued = _issue_token(user_id, "verify", normalized)
    token = issued["token"]
    subject = "Verify your MasterNoder email"
    body = (
        f"Verify your email for account {user_id}.\n\n"
        f"Verification token: {token}\n"
        f"Expires: {issued['expires_at']}\n\n"
        "Enter this token on your profile Security tab under Email recovery."
    )
    sent = _send_verification_email(normalized, subject, body)
    result = {
        "success": True,
        "user_id": user_id,
        "email_masked": _mask_email(normalized),
        "expires_at": issued["expires_at"],
        "email_delivery_configured": _email_delivery_configured(),
        "message": "Verification email sent." if sent else "Verification token created. Configure SMTP to send automatically.",
    }
    if not sent or (os.getenv("EMAIL_RECOVERY_RETURN_TOKEN") or "").strip().lower() in {"1", "true", "yes", "on"}:
        result["verification_token"] = token
    return result


def confirm_email_verification(user_id: str, token: str) -> Dict[str, Any]:
    email = _consume_token(user_id, token, "verify")
    if not email:
        return {"success": False, "error": "Invalid or expired verification token"}
    row = _user_row(user_id)
    row["verified_at"] = _utcnow().isoformat()
    row.pop("recovery_email", None)
    row.pop("recovery_verified_at", None)
    data = _load()
    data.setdefault("users", {})[user_id] = row
    _index_email(data, email, user_id)
    _save(data)
    saved = _set_profile_email(user_id, email, verified=True)
    if not saved.get("success", True):
        return {"success": False, "error": saved.get("error") or "Could not save verified email"}
    return {"success": True, "user_id": user_id, "email_masked": _mask_email(email), "message": "Email verified."}


def request_email_change(user_id: str, new_email: str, current_password: Optional[str] = None) -> Dict[str, Any]:
    normalized = _normalize_email(new_email)
    if not normalized:
        return {"success": False, "error": "Valid new email required"}
    if normalized == _profile_primary_email(user_id):
        return {"success": False, "error": "New email matches current email"}

    try:
        from backend.services.password_protection_service import get_password_status, verify_password
        if get_password_status(user_id).get("has_password"):
            if not current_password:
                return {"success": False, "error": "Current password required to change email"}
            if not verify_password(user_id, current_password).get("success"):
                return {"success": False, "error": "Current password is incorrect"}
    except Exception:
        pass

    issued = _issue_token(user_id, "change", normalized)
    token = issued["token"]
    subject = "Confirm your MasterNoder email change"
    body = (
        f"Confirm email change for account {user_id}.\n\n"
        f"Confirmation token: {token}\n"
        f"Expires: {issued['expires_at']}\n"
    )
    sent = _send_verification_email(normalized, subject, body)
    result = {
        "success": True,
        "user_id": user_id,
        "email_masked": _mask_email(normalized),
        "expires_at": issued["expires_at"],
        "email_delivery_configured": _email_delivery_configured(),
        "message": "Confirmation email sent to the new address." if sent else "Change token created. Configure SMTP to send automatically.",
    }
    if not sent or (os.getenv("EMAIL_RECOVERY_RETURN_TOKEN") or "").strip().lower() in {"1", "true", "yes", "on"}:
        result["change_token"] = token
    return result


def confirm_email_change(user_id: str, token: str) -> Dict[str, Any]:
    email = _consume_token(user_id, token, "change")
    if not email:
        return {"success": False, "error": "Invalid or expired change token"}
    row = _user_row(user_id)
    row["verified_at"] = _utcnow().isoformat()
    data = _load()
    data.setdefault("users", {})[user_id] = row
    _index_email(data, email, user_id)
    _save(data)
    saved = _set_profile_email(user_id, email, verified=True)
    if not saved.get("success", True):
        return {"success": False, "error": saved.get("error") or "Could not save new email"}
    return {"success": True, "user_id": user_id, "email_masked": _mask_email(email), "message": "Email updated."}


def request_recovery_email(user_id: str, recovery_email: str) -> Dict[str, Any]:
    normalized = _normalize_email(recovery_email)
    if not normalized:
        return {"success": False, "error": "Valid recovery email required"}
    if normalized == _profile_primary_email(user_id):
        return {"success": False, "error": "Recovery email must differ from primary email"}

    issued = _issue_token(user_id, "recovery", normalized)
    token = issued["token"]
    subject = "Confirm your MasterNoder recovery email"
    body = (
        f"Confirm recovery email for account {user_id}.\n\n"
        f"Confirmation token: {token}\n"
        f"Expires: {issued['expires_at']}\n"
    )
    sent = _send_verification_email(normalized, subject, body)
    result = {
        "success": True,
        "user_id": user_id,
        "recovery_email_masked": _mask_email(normalized),
        "expires_at": issued["expires_at"],
        "email_delivery_configured": _email_delivery_configured(),
        "message": "Recovery email confirmation sent." if sent else "Recovery token created. Configure SMTP to send automatically.",
    }
    if not sent or (os.getenv("EMAIL_RECOVERY_RETURN_TOKEN") or "").strip().lower() in {"1", "true", "yes", "on"}:
        result["recovery_token"] = token
    return result


def confirm_recovery_email(user_id: str, token: str) -> Dict[str, Any]:
    email = _consume_token(user_id, token, "recovery")
    if not email:
        return {"success": False, "error": "Invalid or expired recovery token"}
    row = _user_row(user_id)
    row["recovery_email"] = email
    row["recovery_verified_at"] = _utcnow().isoformat()
    _save_user_row(user_id, row)
    return {
        "success": True,
        "user_id": user_id,
        "recovery_email_masked": _mask_email(email),
        "message": "Recovery email confirmed.",
    }


def lookup_user_id_by_email(email: str) -> Optional[str]:
    """Internal lookup for password recovery — not exposed directly to clients."""
    normalized = _normalize_email(email)
    if not normalized:
        return None
    data = _load()
    indexed = (data.get("email_index") or {}).get(normalized)
    if indexed:
        return str(indexed)
    for uid, row in (data.get("users") or {}).items():
        if not isinstance(row, dict):
            continue
        if row.get("recovery_email") == normalized and row.get("recovery_verified_at"):
            return uid
    return _scan_profile_files_for_email(normalized)
