"""Camgirls AI agent personas and platform agent tools."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODELS_FILE = os.path.join(_ROOT, "data", "camgirls_agent_models.json")

_AGENT_TOOLS = [
    {"action": "catalog", "description": "List performers"},
    {"action": "chat", "description": "Send studio chat message"},
    {"action": "gift", "description": "Send a studio gift"},
    {"action": "tip", "description": "Tip performer MN2"},
    {"action": "unlock", "description": "Unlock performer room"},
    {"action": "fan_club", "description": "Join fan club"},
    {"action": "favorite", "description": "Toggle favorite"},
    {"action": "dance", "description": "Request a dance"},
    {"action": "wheel", "description": "Spin prize wheel"},
    {"action": "private", "description": "Start private timer"},
    {"action": "goal", "description": "Get tip goal status"},
    {"action": "offline_message", "description": "Leave offline message"},
    {"action": "voice_status", "description": "Voice/live status"},
    {"action": "studio_catalog", "description": "Studio gifts and dances"},
    {"action": "age_verify", "description": "Record 18+ age gate"},
    {"action": "history", "description": "Chat history"},
]


def _load_models() -> List[Dict[str, Any]]:
    if not os.path.isfile(_MODELS_FILE):
        return []
    try:
        with open(_MODELS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        rows = data.get("agents") if isinstance(data, dict) else data
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def list_agent_models() -> List[Dict[str, Any]]:
    return _load_models()


def agent_for_performer(performer_id: str) -> Optional[Dict[str, Any]]:
    for m in _load_models():
        if m.get("performer_id") == performer_id:
            return m
    return None


def persona_system_prompt(row: Dict[str, Any]) -> Tuple[str, str]:
    name = row.get("display_name") or row.get("id") or "Performer"
    bio = row.get("bio") or ""
    agent = agent_for_performer(str(row.get("id") or ""))
    task = (agent or {}).get("task_kind") or "default"
    if task not in ("speed", "free", "default", "creative"):
        task = "default"
    system = f"You are {name}, a MasterNoder camgirl studio AI persona. Bio: {bio}"
    return system, task


def list_agent_tools() -> List[Dict[str, Any]]:
    return list(_AGENT_TOOLS)


def execute_agent_action(action: str, user_id: str, approved: bool = False, **kwargs) -> Dict[str, Any]:
    action = (action or "").strip().lower()
    mutating = action not in ("catalog", "studio_catalog", "goal", "history", "voice_status", "age_verify")
    if mutating and not approved:
        return {"success": False, "error": "mutating_action_requires_approved_true"}
    if action == "catalog":
        from backend.services.camgirls_service import list_performers_catalog
        return list_performers_catalog(user_id=user_id)
    if action == "chat":
        from backend.services.camgirls_service import chat_with_performer
        return chat_with_performer(user_id, kwargs.get("performer_id", ""), kwargs.get("message", ""))
    if action == "tip":
        from backend.services.camgirls_service import tip_performer
        return tip_performer(user_id, kwargs.get("performer_id", ""), float(kwargs.get("amount") or 0))
    if action == "unlock":
        from backend.services.camgirls_service import unlock_performer
        return unlock_performer(user_id, kwargs.get("performer_id", ""))
    if action == "studio_catalog":
        from backend.services.camgirls_studio_service import studio_catalog
        return studio_catalog()
    return {"success": False, "error": f"unknown_action:{action}"}
