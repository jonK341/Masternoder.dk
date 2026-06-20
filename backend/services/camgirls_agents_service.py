"""Camgirls AI companion agents — persona models, agent-native API actions."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODELS_FILE = os.path.join(_BASE, "data", "camgirls_agent_models.json")
_MODELS_CACHE: Dict[str, Any] = {"mtime": 0.0, "models": {}, "by_performer": {}}

AGENT_TOOLS: List[Dict[str, Any]] = [
    {
        "action": "catalog",
        "method": "GET",
        "path": "/api/camgirls/performers",
        "mutating": False,
        "description": "List performer catalog with unlock state for user_id.",
    },
    {
        "action": "performer",
        "method": "GET",
        "path": "/api/camgirls/performers/{performer_id}",
        "mutating": False,
        "params": ["performer_id"],
        "description": "Single performer profile and age_verified flag.",
    },
    {
        "action": "agents",
        "method": "GET",
        "path": "/api/camgirls/agents",
        "mutating": False,
        "description": "Roster of AI companion agents linked to performers.",
    },
    {
        "action": "age_status",
        "method": "GET",
        "path": "/api/camgirls/age-verify",
        "mutating": False,
        "description": "Whether user_id passed age gate (via performer detail age_verified).",
    },
    {
        "action": "chat",
        "method": "POST",
        "path": "/api/camgirls/chat",
        "mutating": True,
        "params": ["performer_id", "message"],
        "description": "AI persona chat; debits MN2. Requires unlock + age verify. approved=true required.",
    },
    {
        "action": "unlock",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/unlock",
        "mutating": True,
        "params": ["performer_id"],
        "description": "Unlock performer content; debits MN2. approved=true required.",
    },
    {
        "action": "tip",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/tip",
        "mutating": True,
        "params": ["performer_id", "amount_mn2"],
        "description": "Tip performer; debits MN2. approved=true required.",
    },
    {
        "action": "gift",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/gift",
        "mutating": True,
        "params": ["performer_id", "gift_id"],
        "description": "Send catalog gift (rose, heart, etc.); debits MN2. approved=true required.",
    },
    {
        "action": "dance",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/dance",
        "mutating": False,
        "params": ["performer_id", "dance_id"],
        "description": "Request a dance animation + lingo (unlock required).",
    },
    {
        "action": "favorite",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/favorite",
        "mutating": True,
        "params": ["performer_id"],
        "description": "Toggle favorite performer for user_id. approved=true required.",
    },
    {
        "action": "fan_club",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/fan-club",
        "mutating": True,
        "params": ["performer_id"],
        "description": "Join fan club (MN2); unlock required. approved=true required.",
    },
    {
        "action": "offline",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/offline",
        "mutating": True,
        "params": ["performer_id", "message"],
        "description": "Queue offline message. approved=true required.",
    },
    {
        "action": "private_show",
        "method": "POST",
        "path": "/api/camgirls/performers/{performer_id}/private-show",
        "mutating": True,
        "params": ["performer_id", "minutes"],
        "description": "Start timed private show; debits MN2. approved=true required.",
    },
    {
        "action": "studio_catalog",
        "method": "GET",
        "path": "/api/camgirls/studio/catalog",
        "mutating": False,
        "description": "Gifts, dances, moods, scenes, standard program features.",
    },
    {
        "action": "leaderboard",
        "method": "GET",
        "path": "/api/camgirls/performers/{performer_id}/leaderboard",
        "mutating": False,
        "params": ["performer_id"],
        "description": "Top tippers for a performer room.",
    },
    {
        "action": "chat_history",
        "method": "GET",
        "path": "/api/camgirls/performers/{performer_id}/chat/history",
        "mutating": False,
        "params": ["performer_id"],
        "description": "Chat history for unlocked performer.",
    },
]


def _read_models_raw() -> Dict[str, Dict[str, Any]]:
    if not os.path.isfile(_MODELS_FILE):
        return {}
    try:
        mtime = os.path.getmtime(_MODELS_FILE)
    except OSError:
        return {}
    if _MODELS_CACHE.get("mtime") == mtime:
        return _MODELS_CACHE["models"]
    try:
        with open(_MODELS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        models = raw.get("models") if isinstance(raw.get("models"), dict) else {}
        models = {k: v for k, v in models.items() if isinstance(v, dict)}
    except Exception:
        return _MODELS_CACHE.get("models") or {}
    by_performer: Dict[str, Dict[str, Any]] = {}
    for agent_id, model in models.items():
        pid = (model.get("performer_id") or "").strip()
        if pid:
            by_performer[pid] = {"agent_id": agent_id, **model}
    _MODELS_CACHE["mtime"] = mtime
    _MODELS_CACHE["models"] = models
    _MODELS_CACHE["by_performer"] = by_performer
    return models


def list_agent_models() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for agent_id, model in _read_models_raw().items():
        out.append({
            "agent_id": agent_id,
            "name": model.get("name") or agent_id,
            "performer_id": model.get("performer_id"),
            "specialization": model.get("specialization"),
            "llm_task": model.get("llm_task") or "speed",
            "skills": list(model.get("skills") or []),
        })
    return out


def get_agent_model(agent_id: str) -> Optional[Dict[str, Any]]:
    aid = (agent_id or "").strip()
    if not aid:
        return None
    model = _read_models_raw().get(aid)
    if not model:
        return None
    return {"agent_id": aid, **model}


def agent_for_performer(performer_id: str) -> Optional[Dict[str, Any]]:
    pid = (performer_id or "").strip()
    if not pid:
        return None
    _read_models_raw()
    rec = _MODELS_CACHE.get("by_performer", {}).get(pid)
    return dict(rec) if isinstance(rec, dict) else None


def persona_system_prompt(performer_row: Dict[str, Any]) -> tuple[str, str]:
    """Return (system_prompt, llm_task) for chat."""
    name = performer_row.get("display_name") or performer_row.get("id") or "Performer"
    bio = performer_row.get("bio") or performer_row.get("tagline") or ""
    task = str(performer_row.get("llm_task") or "speed")
    custom = (performer_row.get("system_prompt") or "").strip()

    linked = None
    agent_id = (performer_row.get("agent_id") or "").strip()
    if agent_id:
        linked = get_agent_model(agent_id)
    if not linked:
        linked = agent_for_performer(str(performer_row.get("id") or ""))

    if linked:
        task = str(linked.get("llm_task") or task)
        custom = (linked.get("system_prompt") or linked.get("system_prompt_extra") or custom).strip()

    base = (
        f"You are {name}, a performer on MasterNoder.dk camgirls catalog. "
        f"Stay in character. Bio: {bio}. "
        "Reply in 1-3 short sentences. Be warm and playful; no explicit content."
    )
    if custom:
        base = f"{base}\n\nPersona notes: {custom}"
    try:
        from backend.services.camgirls_studio_service import lingo_for_prompt
        extra = lingo_for_prompt(performer_row)
        if extra:
            base = f"{base}\n\nStudio lingo:\n{extra}"
    except Exception:
        pass
    return base, task


def execute_agent_action(
    action: str,
    user_id: str,
    *,
    approved: bool = False,
    performer_id: str = "",
    message: str = "",
    amount_mn2: Optional[float] = None,
) -> Dict[str, Any]:
    """Agent-native dispatch (Game Hub pattern)."""
    tool = next((t for t in AGENT_TOOLS if t["action"] == action), None)
    if not tool:
        return {
            "success": False,
            "error": "unknown_action",
            "available": [t["action"] for t in AGENT_TOOLS],
        }
    if tool.get("mutating") and not approved:
        return {
            "success": False,
            "error": "mutating_action_requires_approved_true",
            "action": action,
        }

    uid = (user_id or "").strip() or "default_user"
    from backend.services import camgirls_service as cg

    if action == "catalog":
        return cg.list_performers_catalog(user_id=uid)
    if action == "performer":
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return cg.get_performer_detail(pid, user_id=uid)
    if action == "agents":
        return {"success": True, "agents": list_agent_models(), "count": len(list_agent_models())}
    if action == "age_status":
        return {
            "success": True,
            "user_id": uid,
            "age_verified": cg.is_age_verified(uid),
        }
    if action == "chat":
        pid = (performer_id or "").strip()
        msg = (message or "").strip()
        if not pid or not msg:
            return {"success": False, "error": "performer_id_and_message_required"}
        return cg.chat_with_performer(uid, pid, msg)
    if action == "unlock":
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return cg.unlock_performer(uid, pid)
    if action == "tip":
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        amt = float(amount_mn2 if amount_mn2 is not None else 10)
        return cg.tip_performer(uid, pid, amt)
    if action == "gift":
        from backend.services.camgirls_studio_service import tip_with_gift
        pid = (performer_id or "").strip()
        gift_id = (message or "").strip()  # agents may pass gift_id via message field
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return tip_with_gift(uid, pid, gift_id=gift_id or None, amount_mn2=amount_mn2)
    if action == "dance":
        from backend.services.camgirls_studio_service import request_dance
        pid = (performer_id or "").strip()
        dance_id = (message or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return request_dance(uid, pid, dance_id)
    if action == "favorite":
        from backend.services.camgirls_social_service import toggle_favorite
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return toggle_favorite(uid, pid)
    if action == "fan_club":
        from backend.services.camgirls_social_service import join_fan_club
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return join_fan_club(uid, pid)
    if action == "offline":
        from backend.services.camgirls_social_service import send_offline_message
        pid = (performer_id or "").strip()
        msg = (message or "").strip()
        if not pid or not msg:
            return {"success": False, "error": "performer_id_and_message_required"}
        return send_offline_message(uid, pid, msg)
    if action == "private_show":
        from backend.services.camgirls_social_service import start_private_show
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        mins = int(amount_mn2 if amount_mn2 is not None else 5)
        return start_private_show(uid, pid, mins)
    if action == "studio_catalog":
        from backend.services.camgirls_studio_service import studio_catalog
        return studio_catalog()
    if action == "leaderboard":
        from backend.services.camgirls_social_service import get_leaderboard
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return get_leaderboard(pid)
    if action == "chat_history":
        pid = (performer_id or "").strip()
        if not pid:
            return {"success": False, "error": "performer_id_required"}
        return cg.get_chat_history(uid, pid)

    return {"success": False, "error": "unhandled_action"}
