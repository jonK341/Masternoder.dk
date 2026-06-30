"""LiveKit voice status and token issuance for camgirls studio."""
from __future__ import annotations

import os
import uuid
from typing import Any, Dict


def public_status() -> Dict[str, Any]:
    configured = bool(os.environ.get("LIVEKIT_URL") and os.environ.get("LIVEKIT_API_KEY"))
    return {
        "configured": configured,
        "mode": "live" if configured else "stub",
        "note": "Voice live when LIVEKIT_URL and LIVEKIT_API_KEY are set.",
    }


def issue_room_token(user_id: str, performer_id: str) -> Dict[str, Any]:
    """Return LiveKit join token when SDK is configured; stub otherwise."""
    user_id = (user_id or "").strip() or "default_user"
    performer_id = (performer_id or "").strip()
    if not performer_id:
        return {"success": False, "error": "performer_id required"}

    status = public_status()
    if not status.get("configured"):
        return {
            "success": True,
            "mode": "stub",
            "room": f"camgirls-{performer_id}",
            "token": None,
            "url": None,
            "note": "LiveKit not configured — voice UI runs in preview mode.",
        }

    try:
        from livekit import api  # type: ignore
    except ImportError:
        return {"success": False, "error": "livekit package not installed"}

    url = os.environ.get("LIVEKIT_URL", "").strip()
    api_key = os.environ.get("LIVEKIT_API_KEY", "").strip()
    api_secret = os.environ.get("LIVEKIT_API_SECRET", "").strip()
    if not api_secret:
        return {"success": False, "error": "LIVEKIT_API_SECRET missing"}

    room = f"camgirls-{performer_id}"
    identity = f"{user_id}-{uuid.uuid4().hex[:8]}"
    grant = api.VideoGrants(room_join=True, room=room)
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity(identity)
        .with_name(user_id)
        .with_grants(grant)
        .to_jwt()
    )
    return {
        "success": True,
        "mode": "live",
        "room": room,
        "token": token,
        "url": url,
        "identity": identity,
    }
