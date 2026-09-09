"""Agent leaderboard MN2 rewards — ties achievements + agent activity to MN2 Bitcoins."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_REWARDS_FILE = os.path.join(_BASE, "data", "agent_leaderboard_rewards.json")

# MN2 payout table by rank (top 10 agents per cycle)
_RANK_REWARDS_MN2 = {
    1: 0.05,
    2: 0.03,
    3: 0.02,
    4: 0.015,
    5: 0.01,
}
_DEFAULT_REWARD = 0.005

_ACHIEVEMENT_MN2 = {
    "first_task_completed": 0.001,
    "task_master_10": 0.003,
    "task_master_50": 0.008,
    "task_master_100": 0.015,
    "debugger_master": 0.005,
    "error_migration_expert": 0.01,
    "perfect_week": 0.004,
    "speed_demon": 0.002,
    "all_tabs_explorer": 0.006,
    "points_collector": 0.012,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_store() -> Dict[str, Any]:
    try:
        with open(_REWARDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"claims": {}, "cycles": [], "last_updated": _now_iso()}


def _save_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_REWARDS_FILE), exist_ok=True)
    data["last_updated"] = _now_iso()
    with open(_REWARDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _agent_score(agent_id: str, progress: Dict[str, Any]) -> int:
    tasks = int(progress.get("tasks_completed") or 0)
    xp = int(progress.get("total_xp") or 0)
    activity = int(progress.get("total_activity") or 0)
    handlers = int(progress.get("handlers_migrated") or 0)
    tabs = len(progress.get("tabs_completed") or [])
    return tasks * 10 + xp + activity * 2 + handlers * 5 + tabs * 25


def build_agent_leaderboard(limit: int = 20) -> Dict[str, Any]:
    """Rank agents by achievement progress + synthetic activity."""
    from backend.services.agent_achievements import agent_achievements
    from backend.services.agent_activity_generator import AgentActivityGenerator

    gen = AgentActivityGenerator()
    progress_map = agent_achievements.achievements.get("progress") or {}
    unlocked_map = agent_achievements.achievements.get("unlocked") or {}

    rows: List[Dict[str, Any]] = []
    agent_ids = set(progress_map.keys()) | set(unlocked_map.keys())

    # Seed known platform agents when empty
    if not agent_ids:
        agent_ids = {
            "podcast_producer_agent", "content_generator_agent", "google_play_agent",
            "lab_create_agent", "lab_project_agent", "analytics_agent",
        }

    for aid in agent_ids:
        prog = progress_map.get(aid) or {}
        score = _agent_score(aid, prog)
        activity = gen.generate_activity("analytical", "comprehensive")
        rows.append({
            "agent_id": aid,
            "score": score,
            "tasks_completed": int(prog.get("tasks_completed") or 0),
            "total_xp": int(prog.get("total_xp") or 0),
            "achievements_unlocked": len((unlocked_map.get(aid) or {})),
            "latest_activity": activity.get("name"),
            "latest_activity_type": activity.get("type"),
            "mn2_reward_tier": _rank_reward_mn2(0),
        })

    rows.sort(key=lambda r: (r["score"], r["achievements_unlocked"]), reverse=True)
    for i, row in enumerate(rows[: max(1, limit)]):
        row["rank"] = i + 1
        row["mn2_reward_tier"] = _rank_reward_mn2(i + 1)
        row["badge"] = ["👑", "🥈", "🥉"][i] if i < 3 else "🤖"

    return {
        "success": True,
        "leaderboard": rows[: max(1, limit)],
        "total_agents": len(rows),
        "reward_currency": "MN2",
        "reward_note": "MasterNoder2 Bitcoins — claim via /api/create-app/agents/leaderboard/claim",
    }


def _rank_reward_mn2(rank: int) -> float:
    if rank <= 0:
        return 0.0
    return float(_RANK_REWARDS_MN2.get(rank, _DEFAULT_REWARD if rank <= 10 else 0.0))


def credit_agent_activity_mn2(
    user_id: str,
    agent_id: str,
    activity_type: str,
    *,
    reference: Optional[str] = None,
) -> Dict[str, Any]:
    """Small MN2 credit when user-linked agent activity is recorded."""
    from backend.services.game_mn2_rewards import credit_mn2

    base = 0.0005
    if activity_type in ("innovation", "problem_solving", "optimization"):
        base = 0.001
    ref = reference or f"agent-activity:{agent_id}:{activity_type}:{user_id}"
    return credit_mn2(
        user_id,
        base,
        source="agent_activity_mn2",
        reference=ref,
        metadata={"agent_id": agent_id, "activity_type": activity_type},
    )


def credit_achievement_mn2(
    user_id: str,
    achievement_id: str,
    agent_id: str,
) -> Dict[str, Any]:
    """Credit MN2 when an agent achievement unlocks for a user-owned agent."""
    from backend.services.game_mn2_rewards import credit_mn2

    amount = float(_ACHIEVEMENT_MN2.get(achievement_id, 0.001))
    ref = f"agent-achievement:{agent_id}:{achievement_id}:{user_id}"
    return credit_mn2(
        user_id,
        amount,
        source="agent_achievement_mn2",
        reference=ref,
        metadata={"agent_id": agent_id, "achievement_id": achievement_id},
    )


def claim_leaderboard_reward(user_id: str, agent_id: str) -> Dict[str, Any]:
    """Claim MN2 for an agent's current leaderboard rank (once per cycle per user)."""
    board = build_agent_leaderboard(limit=50)
    rank_row = next((r for r in board["leaderboard"] if r["agent_id"] == agent_id), None)
    if not rank_row:
        return {"success": False, "error": "agent_not_on_leaderboard"}

    rank = int(rank_row["rank"])
    amount = _rank_reward_mn2(rank)
    if amount <= 0:
        return {"success": False, "error": "no_reward_for_rank", "rank": rank}

    store = _load_store()
    key = f"{user_id}:{agent_id}"
    if key in (store.get("claims") or {}):
        return {"success": False, "error": "already_claimed", "duplicate": True}

    from backend.services.game_mn2_rewards import credit_mn2

    ref = f"agent-leaderboard:{agent_id}:rank{rank}:{user_id}"
    result = credit_mn2(
        user_id,
        amount,
        source="agent_leaderboard_mn2",
        reference=ref,
        metadata={"agent_id": agent_id, "rank": rank},
    )
    if not result.get("success"):
        return result

    store.setdefault("claims", {})[key] = {
        "user_id": user_id,
        "agent_id": agent_id,
        "rank": rank,
        "amount_mn2": amount,
        "claimed_at": _now_iso(),
        "reference": ref,
    }
    _save_store(store)

    # Record agent achievement progress + activity
    try:
        from backend.services.agent_achievements import agent_achievements
        unlocked = agent_achievements.check_achievements(agent_id, "task_completed", {"xp": 10, "activity_points": 5})
        for u in unlocked:
            credit_achievement_mn2(user_id, u["achievement_id"], agent_id)
    except Exception:
        pass

    try:
        from backend.services.activity_events_service import emit
        emit(
            "agent_leaderboard_claim",
            user_id=user_id,
            channel="agents",
            text=f"Claimed {amount} MN2 for agent {agent_id} (rank #{rank})",
            payload={"agent_id": agent_id, "rank": rank, "amount_mn2": amount},
        )
    except Exception:
        pass

    return {
        "success": True,
        "user_id": user_id,
        "agent_id": agent_id,
        "rank": rank,
        "amount_mn2": amount,
        "achievements_checked": True,
    }
