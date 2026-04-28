"""
Feedback loop: tie LLM outcomes to agent skill XP and light task_type preference shifts.
State: logs/agent_feedback/state.json (merge-safe single-file JSON).
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

STATE_PATH = os.path.join(BASE_DIR, "logs", "agent_feedback", "state.json")
MAX_OUTCOMES = 400


def _ensure_dir() -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)


def _load_state() -> Dict[str, Any]:
    _ensure_dir()
    if not os.path.isfile(STATE_PATH):
        return {"task_type_bias": {}, "outcomes": []}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"task_type_bias": {}, "outcomes": []}


def _save_state(data: Dict[str, Any]) -> None:
    _ensure_dir()
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
    except Exception:
        pass


def adjust_task_type_for_user(task_kind: str, default_task_type: str, user_id: Optional[str]) -> str:
    """Nudge task_type if historical success rate favors another (tiny bias)."""
    st = _load_state()
    bias = st.get("task_type_bias", {}).get(task_kind)
    if not bias or not isinstance(bias, dict):
        return default_task_type
    # Pick task_type with highest score if within 0.15 of default's implicit 1.0
    best_t = default_task_type
    best_s = float(bias.get(default_task_type, 1.0))
    for t, s in bias.items():
        if float(s) > best_s + 0.05:
            best_s = float(s)
            best_t = t
    return best_t


def record_llm_outcome(
    trace_id: str,
    user_id: str,
    routing: Dict[str, Any],
    llm_response: Any,
) -> Dict[str, Any]:
    """After an LLM call: log outcome, skill XP on success, bias update."""
    success = bool(getattr(llm_response, "success", False))
    provider = getattr(llm_response, "provider", None)
    task_kind = routing.get("task_kind", "")
    task_type = routing.get("task_type", "")
    skill_name = routing.get("skill_name", "")
    agent_id = routing.get("agent_id", "")

    entry = {
        "at": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "user_id": user_id,
        "task_kind": task_kind,
        "task_type": task_type,
        "agent_id": agent_id,
        "skill_name": skill_name,
        "success": success,
        "provider": provider,
    }

    st = _load_state()
    outcomes = st.get("outcomes", [])
    outcomes.append(entry)
    st["outcomes"] = outcomes[-MAX_OUTCOMES:]

    # Bias: moving average per task_kind × task_type
    tb = st.setdefault("task_type_bias", {}).setdefault(task_kind, {})
    key = task_type
    prev = float(tb.get(key, 1.0))
    delta = 0.08 if success else -0.12
    tb[key] = max(0.1, min(2.0, prev + delta))

    _save_state(st)

    xp_result = None
    if success and user_id and skill_name and user_id not in ("", "default_user", "anonymous"):
        try:
            from backend.services.user_agent_skills import user_agent_skills
            from backend.services.agent_db_service import agent_db_service

            ud = user_agent_skills.get_user_skills(user_id) or {}
            has = any(
                (s.get("skill") == skill_name) for s in (ud.get("skills") or []) if isinstance(s, dict)
            )
            xp = 12
            if has:
                xp_result = user_agent_skills.level_up_skill(user_id, skill_name, experience=xp)
            else:
                xp_result = {"success": False, "skipped": True, "reason": "skill_not_assigned"}
            agent_db_service.record_agent_activity(
                user_id=user_id,
                agent_id=agent_id or "learning_agent",
                action="skill_execution",
                skill=skill_name,
                xp_gained=xp if has else 0,
                metadata={"trace_id": trace_id, "task_kind": task_kind, "provider": provider, "xp_applied": has},
            )
        except Exception as e:
            xp_result = {"success": False, "error": str(e)[:120]}

    return {"logged": True, "skill_xp": xp_result}


def record_manual_outcome(
    trace_id: str,
    user_id: str,
    task_kind: str,
    success: bool,
    user_edited: bool = False,
    points_delta: float = 0.0,
    notes: str = "",
) -> Dict[str, Any]:
    """API hook for UI: user confirmed quality, edit count, points."""
    st = _load_state()
    outcomes = st.get("outcomes", [])
    outcomes.append(
        {
            "at": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "user_id": user_id,
            "task_kind": task_kind,
            "success": success,
            "user_edited": user_edited,
            "points_delta": points_delta,
            "notes": notes[:500],
            "source": "manual",
        }
    )
    st["outcomes"] = outcomes[-MAX_OUTCOMES:]
    if not success and task_kind:
        tb = st.setdefault("task_type_bias", {}).setdefault(task_kind, {})
        for k in list(tb.keys()):
            tb[k] = max(0.1, float(tb[k]) - 0.03)
    _save_state(st)
    return {"success": True}
