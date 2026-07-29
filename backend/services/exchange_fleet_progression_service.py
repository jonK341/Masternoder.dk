"""Fleet bot XP, levels, and reward unlocks for Business Control."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# XP required to complete each level band (level 1 starts at 0 total XP)
_XP_PER_LEVEL = 200

_FLEET_REWARD_TABLE: List[Dict[str, Any]] = [
    {"level": 2, "id": "rookie_clear", "name": "Rookie Clear", "desc": "First successful fleet ticks."},
    {"level": 3, "id": "lane_runner", "name": "Lane Runner", "desc": "Consistent supervisor lane uptime."},
    {"level": 5, "id": "profit_scout", "name": "Profit Scout", "desc": "Live execution attempts logged."},
    {"level": 8, "id": "hot_symbol_hunter", "name": "Hot Symbol Hunter", "desc": "Riding pair-search hot lanes."},
    {"level": 10, "id": "fleet_veteran", "name": "Fleet Veteran", "desc": "Level 10 operator."},
    {"level": 15, "id": "stash_ally", "name": "Stash Ally", "desc": "Treasury / profit synergy."},
    {"level": 20, "id": "risk_ready", "name": "Risk Ready", "desc": "Risk shard mastery."},
    {"level": 25, "id": "commodore", "name": "Commodore", "desc": "Top-tier fleet operator."},
    {"level": 30, "id": "fleet_legend", "name": "Fleet Legend", "desc": "Maximum prestige tier."},
]

_RANK_TITLES: List[Tuple[int, str]] = [
    (30, "Legend"),
    (25, "Commodore"),
    (20, "Ace"),
    (15, "Veteran"),
    (10, "Specialist"),
    (5, "Operator"),
    (2, "Rookie"),
    (1, "Recruit"),
]


def xp_threshold_for_level(level: int) -> int:
    """Total XP required to reach ``level`` (level 1 => 0)."""
    lv = max(1, int(level))
    return _XP_PER_LEVEL * (lv - 1)


def level_from_total_xp(total_xp: int) -> Dict[str, Any]:
    xp = max(0, int(total_xp))
    level = 1 + xp // _XP_PER_LEVEL
    if level > 99:
        level = 99
    floor_xp = xp_threshold_for_level(level)
    next_floor = xp_threshold_for_level(level + 1) if level < 99 else floor_xp + _XP_PER_LEVEL
    in_level = xp - floor_xp
    need = max(1, next_floor - floor_xp)
    return {
        "level": level,
        "total_xp": xp,
        "xp_in_level": in_level,
        "xp_to_next": need,
        "xp_progress_pct": round(100.0 * in_level / need, 1),
    }


def rank_title_for_level(level: int) -> str:
    lv = max(1, int(level))
    for min_lv, title in _RANK_TITLES:
        if lv >= min_lv:
            return title
    return "Recruit"


def rewards_for_level(level: int, already: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    have = set(already or [])
    out: List[Dict[str, Any]] = []
    for row in _FLEET_REWARD_TABLE:
        if int(row["level"]) <= level:
            out.append({**row, "unlocked": row["id"] in have or True})
    return out


def default_progression() -> Dict[str, Any]:
    return {
        "total_xp": 0,
        "tick_count": 0,
        "ok_streak": 0,
        "best_streak": 0,
        "executions": 0,
        "rewards_claimed": [],
        "last_xp_gain": 0,
    }


def _ensure_progression(bot: Dict[str, Any]) -> Dict[str, Any]:
    prog = bot.get("progression")
    if not isinstance(prog, dict):
        prog = default_progression()
        bot["progression"] = prog
        return prog
    # Rehydrate storage shape if an API view was persisted earlier.
    if "rewards" in prog and "rank_title" in prog:
        stored = default_progression()
        for k in (
            "total_xp",
            "tick_count",
            "ok_streak",
            "best_streak",
            "executions",
            "rewards_claimed",
            "last_xp_gain",
        ):
            if k in prog:
                stored[k] = prog[k]
        for k, v in prog.items():
            if k.startswith("_"):
                stored[k] = v
        bot["progression"] = stored
        return stored
    return prog


def xp_gain_for_tick(result: Dict[str, Any], *, ok_streak: int) -> int:
    gain = 10 if result.get("success") else 3
    if result.get("executed"):
        gain += 45
    ex = int(result.get("executed_count") or 0)
    if ex > 0:
        gain += min(60, 15 * ex)
    if result.get("reason") == "below_threshold":
        gain += 5
    if ok_streak >= 5:
        gain += 8
    if ok_streak >= 15:
        gain += 12
    return gain


def apply_tick_progression(bot: Dict[str, Any], result: Dict[str, Any]) -> Dict[str, Any]:
    """Mutate bot progression from one fleet tick result; returns xp awarded."""
    prog = _ensure_progression(bot)
    if result.get("success"):
        prog["ok_streak"] = int(prog.get("ok_streak") or 0) + 1
    else:
        prog["ok_streak"] = 0
    prog["best_streak"] = max(int(prog.get("best_streak") or 0), int(prog.get("ok_streak") or 0))
    prog["tick_count"] = int(prog.get("tick_count") or 0) + 1
    if result.get("executed") or int(result.get("executed_count") or 0) > 0:
        prog["executions"] = int(prog.get("executions") or 0) + max(1, int(result.get("executed_count") or 1))

    gain = xp_gain_for_tick(result, ok_streak=int(prog.get("ok_streak") or 0))
    prog["total_xp"] = int(prog.get("total_xp") or 0) + gain
    prog["last_xp_gain"] = gain

    info = level_from_total_xp(int(prog["total_xp"]))
    claimed = list(prog.get("rewards_claimed") or [])
    for row in _FLEET_REWARD_TABLE:
        rid = row["id"]
        if info["level"] >= int(row["level"]) and rid not in claimed:
            claimed.append(rid)
    prog["rewards_claimed"] = claimed
    return {"xp_gain": gain, **info}


def sync_progression_from_account(bot: Dict[str, Any], acct: Dict[str, Any]) -> None:
    """Light catch-up XP from trading account stats (idempotent per trade_count)."""
    prog = _ensure_progression(bot)
    trades = int(acct.get("trade_count") or 0)
    last_trades = int(prog.get("_sync_trade_count") or 0)
    if trades > last_trades:
        delta = trades - last_trades
        prog["total_xp"] = int(prog.get("total_xp") or 0) + min(500, delta * 25)
        prog["_sync_trade_count"] = trades
    profit = float(acct.get("realized_profit_usd") or 0)
    last_profit = float(prog.get("_sync_profit_usd") or 0)
    if profit > last_profit + 0.01:
        prog["total_xp"] = int(prog.get("total_xp") or 0) + min(200, int((profit - last_profit) * 20))
        prog["_sync_profit_usd"] = round(profit, 4)


def progression_view(bot: Dict[str, Any]) -> Dict[str, Any]:
    prog = _ensure_progression(bot)
    info = level_from_total_xp(int(prog.get("total_xp") or 0))
    level = info["level"]
    claimed = list(prog.get("rewards_claimed") or [])
    rewards = []
    for row in _FLEET_REWARD_TABLE:
        unlocked = level >= int(row["level"])
        rewards.append({
            **row,
            "unlocked": unlocked,
            "claimed": row["id"] in claimed,
        })
    return {
        **info,
        "rank_title": rank_title_for_level(level),
        "tick_count": int(prog.get("tick_count") or 0),
        "ok_streak": int(prog.get("ok_streak") or 0),
        "best_streak": int(prog.get("best_streak") or 0),
        "executions": int(prog.get("executions") or 0),
        "last_xp_gain": int(prog.get("last_xp_gain") or 0),
        "rewards": rewards,
        "rewards_unlocked_count": sum(1 for r in rewards if r.get("unlocked")),
    }


def enrich_fleet_bot(bot: Dict[str, Any], acct: Optional[Dict[str, Any]] = None) -> bool:
    """Sync XP from trading account stats. Returns True if progression storage changed."""
    before = dict(_ensure_progression(bot))
    if acct:
        sync_progression_from_account(bot, acct)
    after = _ensure_progression(bot)
    return before != after


def fleet_progression_summary(bots: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_xp = sum(int((b.get("progression") or {}).get("total_xp") or 0) for b in bots)
    avg_level = 0.0
    if bots:
        avg_level = sum(int((b.get("progression") or {}).get("level") or 1) for b in bots) / len(bots)
    commander = level_from_total_xp(total_xp)
    return {
        "fleet_commander_level": commander["level"],
        "fleet_commander_rank": rank_title_for_level(commander["level"]),
        "fleet_total_xp": total_xp,
        "avg_bot_level": round(avg_level, 2),
        "reward_catalog_size": len(_FLEET_REWARD_TABLE),
        "total_rewards_unlocked": sum(
            int((b.get("progression") or {}).get("rewards_unlocked_count") or 0) for b in bots
        ),
        "xp_per_level": _XP_PER_LEVEL,
    }


def reward_catalog() -> List[Dict[str, Any]]:
    return list(_FLEET_REWARD_TABLE)
