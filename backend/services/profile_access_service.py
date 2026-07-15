"""
Profile access control — session ownership checks and response sanitization.

Lightweight auth model: Flask session user_id must match for mutating or sensitive reads.
Public profile display is allowed when profile_visibility == public (sanitized).
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

from flask import request, session

AccessError = Tuple[Dict[str, Any], int]

_SENSITIVE_SCRAPED_KEYS = frozenset({
    "ip_address", "mac_address", "device_fingerprint", "composite_fingerprint",
    "fingerprint", "raw_ip", "email", "phone",
})

_BLOCKED_PROFILE_UPDATE_KEYS = frozenset({
    "scraped_info", "assigned_agent_ids", "onboarding_data", "user_id", "id",
    "onboarding_complete", "agent_skillset_id", "created_at",
})


def session_user_id() -> Optional[str]:
    """Return bound session user_id if present and not revoked."""
    uid = session.get("user_id")
    if not uid:
        return None
    session_uid = str(uid).strip()
    if not session_uid:
        return None
    try:
        from backend.services.account_session_service import is_session_revoked
        if is_session_revoked(session_uid, request.headers.get("User-Agent", ""), request.remote_addr or ""):
            session.pop("user_id", None)
            return None
    except Exception:
        pass
    return session_uid


def profile_visibility(user_id: str) -> str:
    """Return public | private | friends (default public for legacy profiles)."""
    try:
        from backend.services.user_onboarding import user_onboarding
        profile = user_onboarding.get_user_profile(user_id)
        if not profile:
            return "public"
        prefs = profile.get("preferences") or {}
        if isinstance(prefs, str):
            prefs = json.loads(prefs or "{}")
        vis = str((prefs or {}).get("profile_visibility") or "public").strip().lower()
        return vis if vis in ("public", "private", "friends") else "public"
    except Exception:
        return "public"


def is_owner(target_user_id: str) -> bool:
    session_uid = session_user_id()
    return bool(session_uid and session_uid == str(target_user_id or "").strip())


def require_profile_owner(
    target_user_id: str,
    *,
    allow_default_guest: bool = False,
) -> Optional[AccessError]:
    """Require session user_id to match target. Returns (payload, status) or None if allowed."""
    target = str(target_user_id or "").strip()
    if not target:
        return {"success": False, "error": "user_id required"}, 400

    session_uid = session_user_id()
    if session_uid:
        if session_uid != target:
            return {"success": False, "error": "Forbidden: not your account"}, 403
        return None

    if allow_default_guest and target.lower() == "default_user":
        return None

    return {"success": False, "error": "Authentication required — log in or bind session"}, 401


def require_profile_read(target_user_id: str) -> Optional[AccessError]:
    """Owner always allowed; others only when profile is public (sanitized by caller)."""
    target = str(target_user_id or "").strip()
    if not target:
        return {"success": False, "error": "user_id required"}, 400
    if is_owner(target):
        return None
    if profile_visibility(target) == "public":
        return None
    return {"success": False, "error": "Profile is private"}, 403


def sanitize_scraped_info(info: Any) -> Dict[str, Any]:
    """Strip raw identifiers from scraped info before sending to clients."""
    if not info:
        return {}
    if isinstance(info, str):
        try:
            info = json.loads(info)
        except Exception:
            return {}
    if not isinstance(info, dict):
        return {}

    def _clean(obj: Any) -> Any:
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if k in _SENSITIVE_SCRAPED_KEYS:
                    continue
                if k == "ip_address" and v:
                    out["ip_anonymized"] = str(v).split(".")[0] + ".x.x.x" if "." in str(v) else "hidden"
                    continue
                out[k] = _clean(v)
            return out
        if isinstance(obj, list):
            return [_clean(x) for x in obj]
        return obj

    return _clean(info)


def sanitize_profile_record(profile: Dict[str, Any], *, is_owner_view: bool) -> Dict[str, Any]:
    """Remove sensitive fields from a raw profile dict for non-owner viewers."""
    if not profile:
        return {}
    if is_owner_view:
        out = dict(profile)
        if "scraped_info" in out:
            out["scraped_info"] = sanitize_scraped_info(out.get("scraped_info"))
        return out

    out = {
        "user_id": profile.get("user_id"),
        "username": profile.get("username"),
        "onboarding_complete": profile.get("onboarding_complete"),
        "agent_skillset_id": profile.get("agent_skillset_id"),
        "created_at": profile.get("created_at"),
    }
    prefs = profile.get("preferences") or {}
    if isinstance(prefs, str):
        try:
            prefs = json.loads(prefs or "{}")
        except Exception:
            prefs = {}
    if isinstance(prefs, dict):
        safe_prefs = {
            k: prefs[k]
            for k in ("display_name", "bio", "avatar_url", "profile_visibility", "profile_theme")
            if k in prefs
        }
        out["preferences"] = safe_prefs
    return out


def sanitize_display_payload(result: Dict[str, Any], *, is_owner_view: bool) -> Dict[str, Any]:
    """Sanitize get_profile_display / aggregated payload for non-owner viewers."""
    if not result or is_owner_view:
        return result
    out = dict(result)
    prof = out.get("profile")
    if isinstance(prof, dict):
        prof = dict(prof)
        prof.pop("scraped_info", None)
        prof.pop("preferences", None)
        out["profile"] = prof
    for key in (
        "shop_summary", "password_status", "lab_logbook", "unified_points",
        "leaderboard_snippet", "activity_feed", "my_agents", "trophies_list",
    ):
        out.pop(key, None)
    return out


def validate_profile_update(update_data: Dict[str, Any]) -> Optional[str]:
    """Return error message if update_data contains blocked keys or invalid shape."""
    if not isinstance(update_data, dict) or not update_data:
        return "update_data must be a non-empty object"
    blocked = _BLOCKED_PROFILE_UPDATE_KEYS.intersection(update_data.keys())
    if blocked:
        return f"Cannot update protected fields: {', '.join(sorted(blocked))}"
    prefs = update_data.get("preferences")
    if prefs is not None and not isinstance(prefs, dict):
        return "preferences must be an object"
    return None


def profile_services_health() -> Dict[str, Any]:
    """Lightweight readiness probe for profile stack dependencies."""
    import os

    checks: Dict[str, Any] = {}
    ok = True
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    progress_dir = os.path.join(base, "logs", "onboarding_progress")
    profiles_dir = os.path.join(base, "logs", "user_profiles")
    checks["onboarding_storage"] = os.path.isdir(progress_dir)
    checks["profile_file_storage"] = os.path.isdir(profiles_dir)
    if not checks["onboarding_storage"]:
        ok = False

    try:
        import importlib.util
        checks["user_onboarding_module"] = importlib.util.find_spec("backend.services.user_onboarding") is not None
    except Exception as exc:
        checks["user_onboarding_module"] = str(exc)

    try:
        checks["user_profile_module"] = importlib.util.find_spec("backend.services.user_profile") is not None
    except Exception as exc:
        checks["user_profile_module"] = str(exc)

    return {"success": ok, "status": "ready" if ok else "degraded", "checks": checks}


def check_profile_write_access(requested_user_id: str) -> Optional[str]:
    """Return error message when caller may not mutate the requested account."""
    err = require_profile_owner(requested_user_id, allow_default_guest=True)
    if err:
        return str(err[0].get("error") or "Forbidden")
    return None
