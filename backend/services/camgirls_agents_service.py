"""Camgirls AI companion agents — persona models, agent-native API actions."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_MODELS_FILE = os.path.join(_BASE, "data", "camgirls_agent_models.json")

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
]


def _read_models_raw() -> Dict[str, Dict[str, Any]]:
    if not os.path.isfile(_MODELS_FILE):
        return {}
    try:
        with open(_MODELS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
        models = raw.get("models") if isinstance(raw.get("models"), dict) else {}
        return {k: v for k, v in models.items() if isinstance(v, dict)}
    except Exception:
        return {}


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
    for agent_id, model in _read_models_raw().items():
        if (model.get("performer_id") or "").strip() == pid:
            return {"agent_id": agent_id, **model}
    return None


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

    return {"success": False, "error": "unhandled_action"}
