"""
Central router: task kind → agent skill + LLM task_type + provider chain, with telemetry.
Use with agent_feedback_loop for outcomes and skill XP. See GET /api/agents/capability-map.
"""
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# task_kind → default agent, skill name (user_agent_skills / skillset), llm task_type
TASK_ROUTING_TABLE: Dict[str, Dict[str, Any]] = {
    "plan_video": {
        "agent_id": "content_generator_agent",
        "skill_name": "generate_video",
        "task_type": "reason",
        "description": "Video plan / structure",
    },
    "script_outline": {
        "agent_id": "content_generator_agent",
        "skill_name": "ai_assist_task",
        "task_type": "speed",
        "description": "Fast outline / beats",
    },
    "code_assist": {
        "agent_id": "content_generator_agent",
        "skill_name": "ai_assist_task",
        "task_type": "code",
        "description": "Code generation / fix",
    },
    "chat_general": {
        "agent_id": "learning_agent",
        "skill_name": "ai_nice_and_easy",
        "task_type": "default",
        "description": "General assistant chat",
    },
    "analytics_summarize": {
        "agent_id": "analytics_agent",
        "skill_name": "track_metrics",
        "task_type": "context",
        "description": "Summarize metrics / stats",
    },
    "deep_reasoning": {
        "agent_id": "learning_agent",
        "skill_name": "ai_follow_user_action",
        "task_type": "reason",
        "description": "Strategy / long reasoning",
    },
    "cheap_fast": {
        "agent_id": "content_generator_agent",
        "skill_name": "ai_assist_task",
        "task_type": "free",
        "description": "Free-tier only routing",
    },
    "judge_output": {
        "agent_id": "content_generator_agent",
        "skill_name": "ai_assist_task",
        "task_type": "reason",
        "description": "Quality / criticism evaluation",
    },
    "casino_bet_plan": {
        "agent_id": "casino_kelly_agent",
        "skill_name": "kelly_sizing",
        "task_type": "reason",
        "description": "Casino bet sizing and game selection",
    },
}


def _telemetry_path() -> str:
    d = os.path.join(BASE_DIR, "logs", "agent_router")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "traces.jsonl")


def _append_trace(entry: Dict[str, Any]) -> None:
    try:
        with open(_telemetry_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def route(
    task_kind: str,
    user_id: Optional[str] = None,
    override_task_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Resolve task_kind to agent_id, skill_name, task_type (for llm_service.chat/complete),
    and provider chain preview. Does not call the LLM.
    """
    row = TASK_ROUTING_TABLE.get(task_kind)
    if not row:
        row = TASK_ROUTING_TABLE["chat_general"]
        resolved_kind = "chat_general"
        fallback_kind = task_kind
    else:
        resolved_kind = task_kind
        fallback_kind = None

    task_type = override_task_type or row["task_type"]
    try:
        from backend.services.agent_feedback_loop import adjust_task_type_for_user
        task_type = adjust_task_type_for_user(resolved_kind, task_type, user_id)
    except Exception:
        pass

    try:
        from backend.services.llm_service import _provider_chain_for
        chain = _provider_chain_for(task_type)
    except Exception:
        chain = []

    trace_id = str(uuid.uuid4())
    out = {
        "trace_id": trace_id,
        "task_kind": resolved_kind,
        "task_kind_requested": task_kind,
        "fallback_from_unknown_kind": fallback_kind,
        "agent_id": row["agent_id"],
        "skill_name": row["skill_name"],
        "task_type": task_type,
        "description": row.get("description", ""),
        "provider_chain": chain,
        "at": datetime.now(timezone.utc).isoformat(),
    }
    _append_trace({"event": "route", **out, "user_id": user_id})
    return out


def routed_chat(
    messages: List[Dict[str, str]],
    task_kind: str,
    user_id: str,
    **chat_kwargs: Any,
):
    """
    Single entry: route → llm_service.chat with task_type → record outcome + optional skill XP.
    Returns (llm_response, routing_dict).
    """
    from backend.services.llm_service import chat

    r = route(task_kind, user_id=user_id)
    task_type = r["task_type"]
    resp = chat(messages, task_type=task_type, **chat_kwargs)
    try:
        from backend.services.agent_feedback_loop import record_llm_outcome

        record_llm_outcome(r["trace_id"], user_id, r, resp)
    except Exception:
        pass
    return resp, r


def list_task_kinds() -> List[Dict[str, Any]]:
    """For capability map and docs."""
    return [{"task_kind": k, **v} for k, v in sorted(TASK_ROUTING_TABLE.items())]
