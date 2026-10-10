"""
Lightweight camgirls platform status — online/availability without full studio service.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List

from backend.services.camgirls_livekit_service import public_status as livekit_status

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _performers_paths() -> List[str]:
    return [
        os.path.join(_ROOT, "data", "camgirls_performers_production.json"),
        os.path.join(_ROOT, "data", "camgirls_performers.json"),
    ]


def _load_performers() -> List[Dict[str, Any]]:
    for path in _performers_paths():
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [p for p in data if isinstance(p, dict)]
            if isinstance(data, dict):
                rows = data.get("performers")
                if isinstance(rows, list):
                    return [p for p in rows if isinstance(p, dict)]
        except Exception:
            continue
    return []


def platform_status() -> Dict[str, Any]:
    """
    AI performers are always available for chat/studio; voice is live only when LiveKit is configured.
    """
    livekit = livekit_status()
    performers: List[Dict[str, Any]] = []

    try:
        from backend.services.camgirls_service import list_performers_catalog

        cat = list_performers_catalog(user_id="default_user", lite=True)
        performers = cat.get("performers") if isinstance(cat.get("performers"), list) else []
    except Exception:
        performers = _load_performers()

    roster: List[Dict[str, Any]] = []
    for p in performers:
        pid = str(p.get("id") or "")
        roster.append(
            {
                "id": pid,
                "display_name": p.get("display_name") or pid,
                "online": True,
                "studio_available": bool(p.get("ai_enabled", True)),
                "voice_mode": "live" if livekit.get("configured") else "stub",
                "avatar_url": p.get("avatar_url"),
                "tagline": p.get("tagline"),
            }
        )
    return {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "studio_mode": "ai_always_on",
        "performers_count": len(roster),
        "performers_online": len(roster),
        "voice_live": bool(livekit.get("configured")),
        "livekit": livekit,
        "performers": roster,
        "note": (
            "Performers are AI studio personas — chat, gifts, and dances work 24/7. "
            "Real-time voice needs LIVEKIT_* env vars (currently stub on prod)."
        ),
    }
