"""
Progression quest system — 90 levels of entertainment across 9 chapters.
File-backed per-user state in data/quest_progression/{user_id}.json.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

TOTAL_LEVELS = 90
LEVELS_PER_CHAPTER = 10

_CHAPTERS = [
    {"id": 1, "name": "Pilot's Run", "tier": "beginner", "icon": "🎬"},
    {"id": 2, "name": "Battle Circus", "tier": "apprentice", "icon": "⚔️"},
    {"id": 3, "name": "Social Stage", "tier": "journeyman", "icon": "💬"},
    {"id": 4, "name": "Star Voyager", "tier": "adept", "icon": "🌟"},
    {"id": 5, "name": "Casino Nights", "tier": "expert", "icon": "🎰"},
    {"id": 6, "name": "Trophy Vault", "tier": "veteran", "icon": "🏆"},
    {"id": 7, "name": "AI Odyssey", "tier": "master", "icon": "🤖"},
    {"id": 8, "name": "MN2 Frontier", "tier": "champion", "icon": "🪙"},
    {"id": 9, "name": "Legend's Encore", "tier": "legend", "icon": "👑"},
]

_OBJECTIVE_POOL = {
    1: [
        ("create_video", "Spin the Reel", "Generate your first AI video on the platform.", 1),
        ("earn_xp", "Spark of XP", "Earn {t} XP across any activity.", None),
        ("visit_tab", "Lobby Tour", "Open the Generator and breathe in the neon.", 1),
        ("send_message", "First Ping", "Send {t} chat message(s) to the AI crew.", None),
        ("earn_quest_points", "Scroll Starter", "Bank {t} quest points from any source.", None),
        ("create_video", "Double Feature", "Create {t} AI videos.", None),
        ("explore_feature", "Feature Safari", "Discover {t} platform feature(s).", None),
        ("earn_game_points", "Arcade Tap", "Earn {t} game points.", None),
        ("read_compendium", "Lore Peek", "Read {t} compendium page(s).", None),
        ("login_streak", "Daily Debut", "Log in on {t} consecutive day(s).", None),
    ],
    2: [
        ("win_battle", "First Blood", "Win {t} arena battle(s).", None),
        ("complete_battle", "Arena Warm-up", "Complete {t} battle(s) win or lose.", None),
        ("earn_battle_points", "War Chest", "Earn {t} battle points.", None),
        ("win_battle", "Triple Threat", "Win {t} battles in a row of play.", None),
        ("visit_tab", "Battle Briefing", "Open the Battle page and scout the field.", 1),
        ("earn_xp", "Combat XP", "Earn {t} XP from battles and hunts.", None),
        ("win_battle", "Gladiator", "Win {t} total battles.", None),
        ("complete_battle", "Marathon Clash", "Complete {t} battles this chapter.", None),
        ("earn_battle_points", "Blood & Glory", "Stack {t} battle points.", None),
        ("win_battle", "Champion's Gate", "Win {t} battles to clear the circus.", None),
    ],
    3: [
        ("send_message", "Icebreaker", "Send {t} chat messages.", None),
        ("visit_tab", "Social Hour", "Visit the Social hub.", 1),
        ("add_friend", "Crew Recruit", "Add {t} friend(s) to your crew.", None),
        ("send_message", "Town Crier", "Send {t} messages across sessions.", None),
        ("visit_tab", "Chat Lounge", "Open Chat and leave a mark.", 1),
        ("earn_social_points", "Network Effect", "Earn {t} social points.", None),
        ("send_message", "Dialogue Tree", "Send {t} thoughtful messages.", None),
        ("visit_tab", "Profile Polish", "Visit your Profile page.", 1),
        ("add_friend", "Squad Goals", "Grow your crew to {t} friend(s).", None),
        ("send_message", "Encore Applause", "Send {t} messages — the stage is yours.", None),
    ],
    4: [
        ("investigate_starmap", "Star Fix", "Investigate {t} Star Map point(s).", None),
        ("visit_tab", "Cartographer", "Open Star Map 25.", 1),
        ("investigate_starmap", "Segmentum Scout", "Chart {t} map nodes.", None),
        ("earn_xp", "Cosmic Grind", "Earn {t} XP while exploring.", None),
        ("investigate_starmap", "Nebula Navigator", "Investigate {t} points on the map.", None),
        ("visit_tab", "Galaxy Guide", "Revisit Star Map with intent.", 1),
        ("investigate_starmap", "Deep Scan", "Complete {t} map investigations.", None),
        ("read_story", "Stellar Tale", "Read {t} hunter story/stories.", None),
        ("investigate_starmap", "Void Walker", "Investigate {t} map locations.", None),
        ("investigate_starmap", "Constellation Crown", "Master {t} map points this arc.", None),
    ],
    5: [
        ("casino_bet", "Lucky Penny", "Place {t} casino bet(s).", None),
        ("visit_tab", "Velvet Rope", "Enter the Casino floor.", 1),
        ("casino_bet", "High Roller", "Place {t} bets across games.", None),
        ("earn_coins", "Coin Shower", "Earn {t} coins from play.", None),
        ("casino_bet", "Jackpot Hunt", "Place {t} casino wagers.", None),
        ("claim_casino_quest", "Daily Dealer", "Claim {t} casino daily quest(s).", None),
        ("casino_bet", "Table Hopping", "Place {t} bets on any table.", None),
        ("earn_coins", "House Money", "Stack {t} coins.", None),
        ("casino_bet", "All-In Attitude", "Place {t} bold bets.", None),
        ("casino_bet", "Casino Kingpin", "Close the night with {t} bets.", None),
    ],
    6: [
        ("unlock_trophy", "Bronze Gleam", "Unlock {t} trophy/trophies.", None),
        ("visit_tab", "Hall of Fame", "Open the Trophies page.", 1),
        ("unlock_trophy", "Collector's Eye", "Unlock {t} trophies.", None),
        ("earn_trophy_points", "Trophy Score", "Earn {t} trophy points.", None),
        ("unlock_trophy", "Case Cracker", "Unlock {t} new trophies.", None),
        ("claim_trophy_quest", "Quest Trophy", "Claim {t} trophy quest(s).", None),
        ("unlock_trophy", "Vault Raider", "Unlock {t} trophies this chapter.", None),
        ("earn_trophy_points", "Prestige Stack", "Bank {t} trophy points.", None),
        ("unlock_trophy", "Relic Hunter", "Unlock {t} rare trophies.", None),
        ("unlock_trophy", "Vault Master", "Unlock {t} trophies to seal the vault.", None),
    ],
    7: [
        ("send_message", "Prompt Artist", "Send {t} AI chat messages.", None),
        ("visit_tab", "Agent Deck", "Open the Agents page.", 1),
        ("create_video", "AI Director", "Generate {t} AI videos.", None),
        ("send_message", "Neural Banter", "Chat {t} times with agents.", None),
        ("visit_tab", "Skill Lab", "Browse agent skill sets.", 1),
        ("earn_xp", "Machine Muse", "Earn {t} XP via AI tools.", None),
        ("send_message", "Deep Context", "Send {t} messages to the AI stack.", None),
        ("create_video", "Render Prophet", "Create {t} videos with AI.", None),
        ("send_message", "Odyssey End", "Send {t} messages — singularity near.", None),
        ("complete_ai_quest", "Daily Oracle", "Complete {t} AI daily quest(s).", None),
    ],
    8: [
        ("visit_tab", "Wallet Walk", "Open your MN2 wallet on Profile.", 1),
        ("earn_mn2", "Micro Mint", "Earn {t} MN2 (any source).", None),
        ("visit_tab", "Shop Window", "Browse the Shop.", 1),
        ("spend_coins", "Market Flip", "Spend {t} coins in the shop.", None),
        ("earn_mn2", "Stake Whisper", "Earn {t} MN2 rewards.", None),
        ("visit_tab", "Explorer Node", "Visit the Explorer.", 1),
        ("earn_coins", "Treasury", "Hold {t} coins earned total.", None),
        ("earn_mn2", "Frontier Forge", "Accumulate {t} MN2.", None),
        ("claim_quest", "Reward Loop", "Claim {t} quest reward(s).", None),
        ("earn_mn2", "MN2 Magnate", "Bank {t} MN2 to rule the frontier.", None),
    ],
    9: [
        ("earn_xp", "Grand XP", "Earn {t} total XP.", None),
        ("earn_quest_points", "Quest Legend", "Bank {t} quest points.", None),
        ("complete_level", "Perfectionist", "Complete {t} progression level(s).", None),
        ("win_battle", "Final Boss", "Win {t} battles as a legend.", None),
        ("unlock_trophy", "Crown Jewels", "Unlock {t} trophies.", None),
        ("create_video", "Director's Cut", "Create {t} epic videos.", None),
        ("investigate_starmap", "Ultimate Map", "Investigate {t} map points.", None),
        ("earn_game_points", "Game God", "Earn {t} game points.", None),
        ("login_streak", "Eternal Flame", "Maintain a {t}-day login streak.", None),
        ("earn_xp", "Encore Eternal", "Earn {t} XP — the legend never fades.", None),
    ],
}

_TAB_OBJECTIVES = {
    "visit_tab": {"generator": "generator", "battle": "battle", "social": "social",
                  "starmap25": "starmap25", "casino": "casino", "trophies": "trophies",
                  "agents": "agents", "shop": "shop", "profile": "profile", "explorer": "explorer"},
}

_LEVEL_CACHE: Optional[List[Dict[str, Any]]] = None


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _progress_dir() -> str:
    d = os.path.join(_base(), "data", "quest_progression")
    os.makedirs(d, exist_ok=True)
    return d


def _state_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_progress_dir(), f"{safe}.json")


def _load_state(user_id: str) -> Dict[str, Any]:
    path = _state_path(user_id)
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_state(user_id: str, state: Dict[str, Any]) -> None:
    with open(_state_path(user_id), "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _target_for_level(level_num: int, base: Optional[int]) -> int:
    if base is not None:
        return base
    chapter = (level_num - 1) // LEVELS_PER_CHAPTER + 1
    slot = (level_num - 1) % LEVELS_PER_CHAPTER
    return max(1, 1 + chapter + slot * (1 + chapter // 2))


def _rewards_for_level(level_num: int) -> Dict[str, float]:
    return {
        "quest_points": 25 + level_num * 8,
        "xp": 15 + level_num * 5,
        "mn2": round(0.001 + level_num * 0.00035, 6),
        "coins": 5 + level_num * 2,
    }


def _initialize_quest_templates() -> List[Dict[str, Any]]:
    global _LEVEL_CACHE
    if _LEVEL_CACHE is not None:
        return _LEVEL_CACHE

    levels: List[Dict[str, Any]] = []
    for n in range(1, TOTAL_LEVELS + 1):
        chapter_idx = (n - 1) // LEVELS_PER_CHAPTER
        chapter = _CHAPTERS[chapter_idx]
        slot = (n - 1) % LEVELS_PER_CHAPTER
        obj_type, title, desc_tpl, fixed_target = _OBJECTIVE_POOL[chapter["id"]][slot]
        target = _target_for_level(n, fixed_target)
        desc = desc_tpl.replace("{t}", str(target))
        tab = None
        if obj_type == "visit_tab":
            tabs = list(_TAB_OBJECTIVES["visit_tab"].values())
            tab = tabs[slot % len(tabs)]

        levels.append({
            "level": n,
            "chapter": chapter["id"],
            "chapter_name": chapter["name"],
            "tier": chapter["tier"],
            "icon": chapter["icon"],
            "title": title,
            "description": desc,
            "objective": {
                "type": obj_type,
                "target": target,
                **({"tab": tab} if tab else {}),
            },
            "rewards": _rewards_for_level(n),
        })

    _LEVEL_CACHE = levels
    return levels


def get_all_levels() -> List[Dict[str, Any]]:
    return list(_initialize_quest_templates())


def get_chapters() -> List[Dict[str, Any]]:
    return [dict(c, level_start=(c["id"] - 1) * LEVELS_PER_CHAPTER + 1,
                 level_end=c["id"] * LEVELS_PER_CHAPTER) for c in _CHAPTERS]


def _get_quest_level(completed_count: int) -> str:
    if completed_count >= 80:
        return "legend"
    if completed_count >= 60:
        return "champion"
    if completed_count >= 50:
        return "veteran"
    if completed_count >= 40:
        return "expert"
    if completed_count >= 30:
        return "adept"
    if completed_count >= 20:
        return "journeyman"
    if completed_count >= 10:
        return "apprentice"
    return "beginner"


def _get_stage_rewards(level_def: Dict[str, Any]) -> Dict[str, float]:
    return dict(level_def.get("rewards") or {})


def _metric_value(user_id: str, metric: str, state: Dict[str, Any]) -> int:
    """Read cumulative metric for objective sync."""
    try:
        from backend.services.unified_points_database import unified_points_db
        raw = unified_points_db.get_all_points(user_id) or {}
        pts = raw.get("points", raw) if isinstance(raw, dict) else {}
    except Exception:
        pts = {}

    if metric == "earn_xp":
        return int(pts.get("xp_total") or 0)
    if metric == "earn_quest_points":
        return int(pts.get("quest_points") or 0)
    if metric == "earn_game_points":
        return int(pts.get("game_points") or 0)
    if metric == "earn_battle_points":
        return int(pts.get("battle_points") or 0)
    if metric == "earn_social_points":
        return int(pts.get("social_points") or 0)
    if metric == "earn_trophy_points":
        return int(pts.get("trophy_points") or 0)
    if metric == "earn_coins":
        return int(pts.get("coins") or 0)
    if metric == "earn_mn2":
        return int(float(pts.get("mn2_balance") or 0) * 10000)
    if metric == "spend_coins":
        return int(state.get("coins_spent") or 0)

    if metric == "create_video":
        try:
            from backend.services.user_engagement import get_generation_history
            hist = get_generation_history(user_id, limit=500) or {}
            return len(hist.get("items") or hist.get("history") or [])
        except Exception:
            return int(state.get("videos_created") or 0)

    if metric == "win_battle":
        try:
            from backend.services.battle_db_service import get_battle_history
            recent = get_battle_history(user_id, limit=500) or []
            return sum(1 for m in recent if m.get("result") == "win")
        except Exception:
            return int(state.get("battles_won") or 0)

    if metric == "complete_battle":
        try:
            from backend.services.battle_db_service import get_battle_history
            return len(get_battle_history(user_id, limit=500) or [])
        except Exception:
            return int(state.get("battles_total") or 0)

    if metric == "unlock_trophy":
        try:
            from backend.services.trophies_db_service import get_user_trophies
            return len(get_user_trophies(user_id) or [])
        except Exception:
            return int(state.get("trophies_unlocked") or 0)

    if metric == "send_message":
        try:
            from backend.services.user_engagement import get_quests
            qdata = get_quests(user_id) or {}
            for q in qdata.get("quests") or []:
                if q.get("id") == "chat_message":
                    return int(q.get("progress") or 0)
        except Exception:
            pass
        return int(state.get("messages_sent") or 0)

    if metric == "investigate_starmap":
        try:
            from backend.services.user_engagement import get_quests
            qdata = get_quests(user_id) or {}
            for q in qdata.get("quests") or []:
                if q.get("id") in ("investigate_starmap", "weekly_starmap"):
                    return int(q.get("progress") or 0)
        except Exception:
            pass
        return int(state.get("starmap_investigations") or 0)

    if metric == "read_compendium":
        try:
            from backend.services.user_engagement import get_compendium_progress
            cp = get_compendium_progress(user_id) or {}
            return int(cp.get("pages_read") or cp.get("read_count") or 0)
        except Exception:
            return int(state.get("compendium_pages") or 0)

    if metric == "read_story":
        try:
            from backend.services.trophy_quest_service import get_story_progress
            return int((get_story_progress(user_id) or {}).get("read_count") or 0)
        except Exception:
            return int(state.get("stories_read") or 0)

    if metric == "login_streak":
        try:
            from backend.services.user_engagement import get_streak
            return int((get_streak(user_id) or {}).get("current_streak") or 0)
        except Exception:
            return int(state.get("login_streak") or 0)

    if metric == "visit_tab":
        return int(state.get("tabs_visited") or 0)

    if metric == "explore_feature":
        return int(state.get("features_explored") or 0)

    if metric == "add_friend":
        return int(state.get("friends_added") or 0)

    if metric == "casino_bet":
        return int(state.get("casino_bets") or 0)

    if metric == "claim_casino_quest":
        return int(state.get("casino_quests_claimed") or 0)

    if metric == "claim_trophy_quest":
        return int(state.get("trophy_quests_claimed") or 0)

    if metric == "complete_ai_quest":
        return int(state.get("ai_quests_completed") or 0)

    if metric == "claim_quest":
        return int(state.get("quests_claimed") or 0)

    if metric == "complete_level":
        return sum(1 for v in (state.get("levels") or {}).values() if v.get("claimed"))

    return int(state.get(metric) or 0)


def _is_unlocked(level_num: int, state: Dict[str, Any]) -> bool:
    if level_num <= 1:
        return True
    prev = (state.get("levels") or {}).get(str(level_num - 1), {})
    return bool(prev.get("claimed"))


def _sync_level(user_id: str, level_def: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    n = level_def["level"]
    key = str(n)
    levels = state.setdefault("levels", {})
    row = dict(levels.get(key) or {"progress": 0, "completed": False, "claimed": False})

    if row.get("claimed"):
        levels[key] = row
        return row

    unlocked = _is_unlocked(n, state)
    row["locked"] = not unlocked
    if not unlocked:
        row["progress"] = 0
        row["completed"] = False
        levels[key] = row
        return row

    obj = level_def["objective"]
    metric = obj["type"]
    target = int(obj.get("target") or 1)
    if metric == "visit_tab" and obj.get("tab"):
        visited = state.get("tabs_visited_set") or []
        if isinstance(visited, list) and obj["tab"] in visited:
            current = 1
        else:
            current = 0
    else:
        current = _metric_value(user_id, metric, state)

    row["progress"] = min(current, target)
    row["completed"] = current >= target
    levels[key] = row
    return row


def _initialize_user_quests(user_id: str) -> Dict[str, Any]:
    state = _load_state(user_id)
    if not state:
        state = {"levels": {}, "tabs_visited_set": [], "created_at": datetime.now(timezone.utc).isoformat()}
    for level_def in _initialize_quest_templates():
        _sync_level(user_id, level_def, state)
    state["last_sync"] = datetime.now(timezone.utc).isoformat()
    _save_state(user_id, state)
    return state


def update_quest_progress(user_id: str, action: str, increment: int = 1, **meta) -> Dict[str, Any]:
    """Record a platform action and re-sync affected progression levels."""
    state = _initialize_user_quests(user_id)
    action = (action or "").strip()

    counters = {
        "create_video": "videos_created",
        "win_battle": "battles_won",
        "complete_battle": "battles_total",
        "send_message": "messages_sent",
        "investigate_starmap": "starmap_investigations",
        "casino_bet": "casino_bets",
        "explore_feature": "features_explored",
        "add_friend": "friends_added",
        "visit_tab": "tabs_visited",
    }
    if action in counters:
        key = counters[action]
        state[key] = int(state.get(key) or 0) + increment

    if action == "visit_tab" and meta.get("tab"):
        tabs = state.setdefault("tabs_visited_set", [])
        if not isinstance(tabs, list):
            tabs = []
        tab = str(meta["tab"])
        if tab not in tabs:
            tabs.append(tab)
        state["tabs_visited_set"] = tabs
        state["tabs_visited"] = len(tabs)

    for level_def in _initialize_quest_templates():
        _sync_level(user_id, level_def, state)

    _save_state(user_id, state)
    return {"success": True, "action": action, "increment": increment}


def claim_level_reward(user_id: str, level_num: int) -> Dict[str, Any]:
    level_num = int(level_num)
    if level_num < 1 or level_num > TOTAL_LEVELS:
        return {"success": False, "error": "invalid_level"}

    state = _initialize_user_quests(user_id)
    key = str(level_num)
    row = (state.get("levels") or {}).get(key)
    level_def = next((l for l in _initialize_quest_templates() if l["level"] == level_num), None)
    if not level_def or not row:
        return {"success": False, "error": "level_not_found"}
    if row.get("claimed"):
        return {"success": True, "already_claimed": True, "level": level_num}
    if not row.get("completed"):
        return {"success": False, "error": "level_not_complete"}

    rewards = _get_stage_rewards(level_def)
    credited = {}
    try:
        from backend.services.unified_points_database import unified_points_db
        if rewards.get("quest_points"):
            unified_points_db.add_points(
                user_id, "quest_points", rewards["quest_points"],
                source="progression_quest", metadata={"level": level_num},
            )
            credited["quest_points"] = rewards["quest_points"]
        if rewards.get("xp"):
            unified_points_db.add_points(
                user_id, "xp_total", rewards["xp"],
                source="progression_quest", metadata={"level": level_num},
            )
            credited["xp"] = rewards["xp"]
        if rewards.get("coins"):
            unified_points_db.add_points(
                user_id, "coins", rewards["coins"],
                source="progression_quest", metadata={"level": level_num},
            )
            credited["coins"] = rewards["coins"]
    except Exception:
        pass

    mn2 = float(rewards.get("mn2") or 0)
    if mn2 > 0:
        try:
            from backend.services.trophy_level_service import _credit_mn2
            if _credit_mn2(user_id, mn2, "progression_quest", metadata={"level": level_num}):
                credited["mn2"] = mn2
        except Exception:
            pass

    row["claimed"] = True
    row["claimed_at"] = datetime.now(timezone.utc).isoformat()
    state["levels"][key] = row
    state["quests_claimed"] = int(state.get("quests_claimed") or 0) + 1
    _save_state(user_id, state)

    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync("quests")
    except Exception:
        pass

    return {"success": True, "level": level_num, "rewards": rewards, "credited": credited}


def get_quest_statistics(user_id: str) -> Dict[str, Any]:
    state = _initialize_user_quests(user_id)
    levels = state.get("levels") or {}
    completed = sum(1 for v in levels.values() if v.get("claimed"))
    in_progress = sum(1 for v in levels.values() if v.get("completed") and not v.get("claimed"))
    return {
        "total_levels": TOTAL_LEVELS,
        "completed": completed,
        "claimable": in_progress,
        "percent": round((completed / TOTAL_LEVELS) * 100, 1) if TOTAL_LEVELS else 0,
        "quest_level": _get_quest_level(completed),
    }


def get_user_quests(user_id: str, chapter: Optional[int] = None) -> Dict[str, Any]:
    """Full progression board for /api/quests/user and quests page."""
    state = _initialize_user_quests(user_id)
    all_defs = _initialize_quest_templates()
    stats = get_quest_statistics(user_id)

    if chapter is not None:
        try:
            ch = int(chapter)
            all_defs = [d for d in all_defs if d["chapter"] == ch]
        except (TypeError, ValueError):
            pass

    level_rows: List[Dict[str, Any]] = []
    active_cards: List[Dict[str, Any]] = []

    for level_def in all_defs:
        n = level_def["level"]
        row = (state.get("levels") or {}).get(str(n), {})
        obj = level_def["objective"]
        target = int(obj.get("target") or 1)
        progress = int(row.get("progress") or 0)
        pct = round(min(100.0, (progress / target) * 100), 1) if target else 0
        entry = {
            "id": f"progression_{n}",
            "level": n,
            "chapter": level_def["chapter"],
            "chapter_name": level_def["chapter_name"],
            "tier": level_def["tier"],
            "name": level_def["title"],
            "title": f"Level {n}: {level_def['title']}",
            "description": level_def["description"],
            "icon": level_def["icon"],
            "locked": bool(row.get("locked")),
            "completed": bool(row.get("completed")),
            "claimed": bool(row.get("claimed")),
            "current_stage": 0,
            "total_stages": 1,
            "level_tier": level_def["tier"],
            "progress": {
                "value": progress,
                "target": target,
                "percent": pct,
            },
            "current_objective": {
                "type": obj["type"],
                "target": target,
                **({"tab": obj.get("tab")} if obj.get("tab") else {}),
            },
            "rewards": _get_stage_rewards(level_def),
            "source": "progression",
            "scope": "level",
        }
        level_rows.append(entry)
        if not entry["claimed"] and not entry["locked"] and len(active_cards) < 6:
            active_cards.append(entry)

    return {
        "success": True,
        "user_id": user_id,
        "quest_level": stats["quest_level"],
        "active_count": stats["total_levels"] - stats["completed"],
        "completed_count": stats["completed"],
        "claimable_count": stats["claimable"],
        "progression": stats,
        "chapters": get_chapters(),
        "quests": active_cards,
        "levels": level_rows,
        "total_levels": TOTAL_LEVELS,
    }


class QuestSystem:
    """Facade for legacy imports."""

    TOTAL_LEVELS = TOTAL_LEVELS

    get_all_levels = staticmethod(get_all_levels)
    get_user_quests = staticmethod(get_user_quests)
    update_quest_progress = staticmethod(update_quest_progress)
    claim_level_reward = staticmethod(claim_level_reward)
    get_quest_statistics = staticmethod(get_quest_statistics)


quest_system = QuestSystem()
