"""D2 — LiveKit voice room token for camgirls private voice sessions."""
from __future__ import annotations

import os
import time
from typing import Any, Dict, Optional

try:
    import jwt as pyjwt
except ImportError:
    pyjwt = None  # type: ignore


def _livekit_config() -> Dict[str, str]:
    return {
        "url": (os.environ.get("LIVEKIT_URL") or "").strip().rstrip("/"),
        "api_key": (os.environ.get("LIVEKIT_API_KEY") or "").strip(),
        "api_secret": (os.environ.get("LIVEKIT_API_SECRET") or "").strip(),
    }


def is_configured() -> bool:
    cfg = _livekit_config()
    return bool(cfg["url"] and cfg["api_key"] and cfg["api_secret"] and pyjwt is not None)


def public_status() -> Dict[str, Any]:
    cfg = _livekit_config()
    return {
        "success": True,
        "configured": is_configured(),
        "livekit_url": cfg["url"] or None,
        "mode": "live" if is_configured() else "stub",
        "note": (
            "Set LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET for real voice rooms."
            if not is_configured()
            else "POST /api/camgirls/livekit/token after unlock to join a voice room."
        ),
        "price_mn2_per_minute": float(os.environ.get("CAMGIRLS_VOICE_MN2_PER_MIN") or 0.5),
    }


def _room_name(performer_id: str, user_id: str) -> str:
    pid = (performer_id or "performer").strip().replace(" ", "_")[:32]
    uid = (user_id or "guest").strip().replace(" ", "_")[:32]
    return f"cam_{pid}_{uid}"[:64]


def _create_token(*, room: str, identity: str, ttl_sec: int = 3600) -> str:
    cfg = _livekit_config()
    if not is_configured():
        raise RuntimeError("livekit_not_configured")
    now = int(time.time())
    payload = {
        "iss": cfg["api_key"],
        "sub": identity,
        "nbf": now,
        "exp": now + max(300, min(ttl_sec, 86400)),
        "video": {
            "room": room,
            "roomJoin": True,
            "canPublish": True,
            "canSubscribe": True,
        },
    }
    return pyjwt.encode(payload, cfg["api_secret"], algorithm="HS256")


def issue_voice_token(
    user_id: str,
    performer_id: str,
    *,
    require_unlock: bool = True,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    pid = (performer_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "auth_required"}
    if not pid:
        return {"success": False, "error": "performer_id_required"}

    if require_unlock:
        try:
            from backend.services.camgirls_service import user_has_unlock
            if not user_has_unlock(uid, pid):
                return {"success": False, "error": "unlock_required", "performer_id": pid}
        except Exception:
            pass

    room = _room_name(pid, uid)
    identity = f"fan_{uid}"[:64]

    if not is_configured():
        return {
            "success": True,
            "mode": "stub",
            "room": room,
            "identity": identity,
            "performer_id": pid,
            "user_id": uid,
            "token": None,
            "livekit_url": None,
            "note": "LiveKit env not set — UI can show voice unavailable until ops configures LIVEKIT_*.",
        }

    try:
        token = _create_token(room=room, identity=identity)
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    cfg = _livekit_config()
    return {
        "success": True,
        "mode": "live",
        "room": room,
        "identity": identity,
        "token": token,
        "livekit_url": cfg["url"],
        "performer_id": pid,
        "user_id": uid,
        "ttl_sec": 3600,
    }
