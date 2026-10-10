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
_NEXT_TODOS_FILE = os.path.join(_ROOT, "data", "camgirls_next_todos.json")

# Studio stack every active AI performer is wired for (UI + API parity).
STUDIO_TECH_FEATURES = [
    "ai_chat",
    "gifts",
    "dances",
    "tip_menu",
    "fan_club",
    "private_timer",
    "wheel",
    "leaderboard",
    "offline_message",
    "favorites",
    "agent_action",
    "mn2_wallet",
    "paypal_checkout",
    "voice_livekit",
]


def paypal_configured() -> bool:
    return bool(
        (os.environ.get("PAYPAL_CLIENT_ID") or "").strip()
        and (os.environ.get("PAYPAL_CLIENT_SECRET") or "").strip()
    )


def _load_next_todos() -> List[Dict[str, Any]]:
    if not os.path.isfile(_NEXT_TODOS_FILE):
        return []
    try:
        with open(_NEXT_TODOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        items = data.get("items") if isinstance(data, dict) else None
        if isinstance(items, list):
            return [i for i in items if isinstance(i, dict)]
    except Exception:
        pass
    return []


def studio_tech_for_performer(
    performer_row: Dict[str, Any],
    *,
    livekit: Dict[str, Any],
    paypal_on: bool,
) -> Dict[str, Any]:
    from backend.services.camgirls_agents_service import agent_for_performer

    pid = str(performer_row.get("id") or "")
    agent = agent_for_performer(pid) or {}
    voice_mode = "live" if livekit.get("configured") else "stub"
    features = list(STUDIO_TECH_FEATURES)
    if not paypal_on:
        features = [f for f in features if f != "paypal_checkout"]
    return {
        "ai_enabled": bool(performer_row.get("ai_enabled", True)),
        "studio_available": bool(performer_row.get("ai_enabled", True)),
        "online": True,
        "voice_mode": voice_mode,
        "payments": ["mn2"] + (["paypal"] if paypal_on else []),
        "features": features,
        "agent_id": agent.get("agent_id"),
        "agent_display_name": agent.get("display_name"),
        "task_kind": agent.get("task_kind") or "default",
        "casino_skill_set": agent.get("casino_skill_set") or [],
    }


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

    paypal_on = paypal_configured()
    try:
        from backend.services.camgirls_studio_service import studio_catalog

        cat = studio_catalog()
        program_features = (
            cat.get("standard_program_features")
            if cat.get("success")
            else ["tip_menu", "gifts", "dances", "fan_club", "private_timer", "wheel", "voice_stub"]
        )
    except Exception:
        program_features = list(STUDIO_TECH_FEATURES)

    roster: List[Dict[str, Any]] = []
    for p in performers:
        pid = str(p.get("id") or "")
        tech = studio_tech_for_performer(p, livekit=livekit, paypal_on=paypal_on)
        roster.append(
            {
                "id": pid,
                "display_name": p.get("display_name") or pid,
                "avatar_url": p.get("avatar_url"),
                "tagline": p.get("tagline"),
                **tech,
            }
        )

    agents_linked = sum(1 for r in roster if r.get("agent_id"))
    next_todos = _load_next_todos()

    try:
        from backend.services.camgirls_catalog_db_service import catalog_source_label

        catalog_source = catalog_source_label()
    except Exception:
        catalog_source = "json"

    return {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "catalog_source": catalog_source,
        "studio_mode": "ai_always_on",
        "performers_count": len(roster),
        "performers_online": len(roster),
        "agents_linked": agents_linked,
        "voice_live": bool(livekit.get("configured")),
        "paypal_configured": paypal_on,
        "livekit": livekit,
        "studio_program_features": program_features,
        "platform_tech": {
            "payments": ["mn2"] + (["paypal"] if paypal_on else []),
            "features": roster[0].get("features") if roster else STUDIO_TECH_FEATURES,
            "agent_tools": "/api/camgirls/agent-tools",
            "agent_action": "/api/camgirls/agent-action",
        },
        "performers": roster,
        "next_todos": next_todos,
        "note": (
            "Performers are AI studio personas — chat, gifts, and dances work 24/7. "
            + (
                "PayPal checkout active for unlock, tip, and gift."
                if paypal_on
                else "PayPal env not set — MN2-only checkout."
            )
            + " "
            + (
                "Voice is live via LiveKit."
                if livekit.get("configured")
                else "Voice preview until LIVEKIT_* is configured."
            )
        ),
    }
