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
    "casino_bet_plan": {
        "agent_id": "casino_kelly_agent",
        "skill_name": "kelly_sizing",
        "task_type": "reason",
        "description": "Kelly-style bet plan for even-money casino games",
    },
    "casino_recovery_plan": {
        "agent_id": "casino_martingale_agent",
        "skill_name": "martingale_lite",
        "task_type": "reason",
        "description": "Conservative loss-recovery bet plan",
    },
    "casino_slot_pick": {
        "agent_id": "casino_slot_hunter_agent",
        "skill_name": "slot_selection",
        "task_type": "speed",
        "description": "Fast slot machine selection",
    },
    "casino_tournament_plan": {
        "agent_id": "casino_tournament_agent",
        "skill_name": "tournament_join",
        "task_type": "reason",
        "description": "Tournament join and scoring strategy",
    },
    "casino_crash_plan": {
        "agent_id": "casino_crash_agent",
        "skill_name": "crash_timing",
        "task_type": "speed",
        "description": "Crash auto-cashout target selection",
    },
    "casino_leaderboard_plan": {
        "agent_id": "casino_leaderboard_agent",
        "skill_name": "leaderboard_analysis",
        "task_type": "reason",
        "description": "Leaderboard gap analysis and bet sizing",
    },
    "judge_output": {
        "agent_id": "content_generator_agent",
        "skill_name": "ai_assist_task",
        "task_type": "reason",
        "description": "Quality / criticism evaluation",
    },
    "log_triage": {
        "agent_id": "ai_intelligence_agent",
        "skill_name": "ai_assist_task",
        "task_type": "context",
        "description": "Triage logs/errors — classify severity and next action",
    },
    "support_copilot": {
        "agent_id": "learning_agent",
        "skill_name": "ai_nice_and_easy",
        "task_type": "speed",
        "description": "Support copilot — fast user help drafts",
    },
    "pricing_brain": {
        "agent_id": "analytics_agent",
        "skill_name": "track_metrics",
        "task_type": "reason",
        "description": "Pricing / monetization advisory from metrics",
    },
    "social_ai_draft": {
        "agent_id": "reporter_agent",
        "skill_name": "broadcast",
        "task_type": "speed",
        "description": "Social/news post draft for platform channels",
    },
    "feed_rank": {
        "agent_id": "social_engagement_agent",
        "skill_name": "track_engagement",
        "task_type": "context",
        "description": "Rank social feed by relevance, friends, and engagement signals",
    },
    "earn_coach": {
        "agent_id": "analytics_agent",
        "skill_name": "track_metrics",
        "task_type": "reason",
        "description": "Earn-hub coaching — next MN2/coin actions from user progress",
    },
    "referral_content": {
        "agent_id": "reporter_agent",
        "skill_name": "broadcast",
        "task_type": "speed",
        "description": "Referral share copy and social snippets",
    },
    "moderation_check": {
        "agent_id": "social_engagement_agent",
        "skill_name": "moderate_content",
        "task_type": "speed",
        "description": "UGC moderation triage for posts and chat",
    },
    "friend_match_hint": {
        "agent_id": "social_engagement_agent",
        "skill_name": "manage_friends",
        "task_type": "context",
        "description": "Friend/crew match suggestions from leaderboard overlap",
    },
    "debugger_challenge": {
        "agent_id": "master_fix_agent",
        "skill_name": "ai_assist_task",
        "task_type": "code",
        "description": "Debugger challenge — route/API fix suggestions",
    },
}

# task_kind → primary HTTP surface for capability map (agent-native parity)
TASK_KIND_ENDPOINTS: Dict[str, str] = {
    "social_ai_draft": "POST /api/agents/router/chat (task_kind=social_ai_draft)",
    "feed_rank": "GET /api/social/feed?ranked=1",
    "earn_coach": "GET /api/social/agent/recommendations",
    "referral_content": "GET /api/social/referrals",
    "moderation_check": "POST /api/social/posts/<id>/moderate",
    "friend_match_hint": "GET /api/social/agent/recommendations (matches)",
    "routed_chat": "POST /api/agents/router/chat",
    "log_triage": "POST /api/agents/router/chat (task_kind=log_triage)",
    "support_copilot": "POST /api/agents/router/chat (task_kind=support_copilot)",
    "pricing_brain": "POST /api/agents/router/chat (task_kind=pricing_brain)",
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

    crypto_reward = None
    if resp.success and user_id and user_id not in ("", "default_user", "anonymous"):
        try:
            from backend.services.agent_crypto_rewards_service import award_agent_action

            crypto_reward = award_agent_action(
                user_id,
                "routed_chat",
                reference=f"routed-chat:{r['trace_id']}",
                metadata={"task_kind": task_kind, "provider": getattr(resp, "provider", None)},
                success=True,
            )
        except Exception:
            pass
    if crypto_reward:
        r["crypto_reward"] = crypto_reward

    return resp, r


def list_task_kinds() -> List[Dict[str, Any]]:
    """For capability map and docs."""
    rows = []
    for k, v in sorted(TASK_ROUTING_TABLE.items()):
        rows.append({"task_kind": k, "endpoint": TASK_KIND_ENDPOINTS.get(k), **v})
    return rows
