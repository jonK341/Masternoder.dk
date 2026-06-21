"""
User Engagement Services
Provides login streaks, daily quests, notifications, achievements, compendium tracking, and favorites.
All data stored per-user in logs/user_engagement/{user_id}/ with JSON files.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENG_DIR = os.path.join(_BASE_DIR, "logs", "user_engagement")
os.makedirs(_ENG_DIR, exist_ok=True)


def _user_dir(user_id: str) -> str:
    d = os.path.join(_ENG_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def _load(user_id: str, filename: str) -> Dict:
    fp = os.path.join(_user_dir(user_id), filename)
    if os.path.isfile(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save(user_id: str, filename: str, data: Dict) -> None:
    fp = os.path.join(_user_dir(user_id), filename)
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)


# ============================== LOGIN STREAKS ==============================

STREAK_BONUSES = {3: 25, 7: 75, 14: 200, 30: 500, 60: 1200, 100: 3000}

def record_login(user_id: str) -> Dict[str, Any]:
    """Record a login and update streak. Call on any authenticated request."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = _load(user_id, "streaks.json")
    if not data:
        data = {"current_streak": 0, "longest_streak": 0, "total_logins": 0, "last_login": None, "login_dates": [], "bonuses_claimed": []}

    last = data.get("last_login")
    if last == today:
        return {"changed": False, **data}

    yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    if last == yesterday:
        data["current_streak"] = data.get("current_streak", 0) + 1
    elif last:
        data["current_streak"] = 1
    else:
        data["current_streak"] = 1

    data["longest_streak"] = max(data.get("longest_streak", 0), data["current_streak"])
    data["total_logins"] = data.get("total_logins", 0) + 1
    data["last_login"] = today

    dates = data.get("login_dates", [])
    if today not in dates:
        dates.append(today)
    data["login_dates"] = dates[-90:]

    bonus_xp = 0
    for threshold, xp in STREAK_BONUSES.items():
        if data["current_streak"] >= threshold and threshold not in data.get("bonuses_claimed", []):
            bonus_xp += xp
            data.setdefault("bonuses_claimed", []).append(threshold)

    if bonus_xp > 0:
        try:
            from backend.services.unified_points_database import unified_points_db
            if unified_points_db:
                unified_points_db.add_points(user_id, "xp_total", bonus_xp, source="login_streak",
                                             metadata={"streak": data["current_streak"]})
        except Exception:
            pass

    _save(user_id, "streaks.json", data)
    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync('login')
    except Exception:
        pass
    return {"changed": True, "bonus_xp": bonus_xp, **data}


def get_streak(user_id: str) -> Dict[str, Any]:
    data = _load(user_id, "streaks.json")
    if not data:
        return {"current_streak": 0, "longest_streak": 0, "total_logins": 0, "last_login": None, "login_dates": []}
    return data


# ============================== DAILY QUESTS ==============================

_QUEST_TEMPLATES = [
    # Daily
    {"id": "generate_video", "title": "Create a Video", "description": "Generate 1 video", "target": 1, "xp_reward": 50, "coin_reward": 5, "type": "daily"},
    {"id": "study_theory", "title": "Study Session", "description": "Study 1 communication psychology theory", "target": 1, "xp_reward": 30, "coin_reward": 3, "type": "daily"},
    {"id": "win_battle", "title": "Battle Victor", "description": "Win 1 battle", "target": 1, "xp_reward": 40, "coin_reward": 5, "type": "daily"},
    {"id": "read_compendium", "title": "Scholar", "description": "Read 2 compendium pages", "target": 2, "xp_reward": 25, "coin_reward": 2, "type": "daily"},
    {"id": "earn_xp", "title": "XP Collector", "description": "Earn 100 XP total", "target": 100, "xp_reward": 50, "coin_reward": 5, "type": "daily"},
    {"id": "investigate_starmap", "title": "Star Map Scout", "description": "Investigate 1 point on Star Map 25", "target": 1, "xp_reward": 35, "coin_reward": 4, "type": "daily"},
    {"id": "chat_message", "title": "Chatter", "description": "Send 1 chat message", "target": 1, "xp_reward": 15, "coin_reward": 1, "type": "daily"},
    {"id": "visit_shop", "title": "Shopper", "description": "Open the Shop page", "target": 1, "xp_reward": 10, "coin_reward": 1, "type": "daily"},
    {"id": "claim_reward", "title": "Reward Claim", "description": "Claim 1 Hunter Game reward", "target": 1, "xp_reward": 20, "coin_reward": 2, "type": "daily"},
    {"id": "earn_game_points", "title": "Game Points", "description": "Earn 25 game points", "target": 25, "xp_reward": 40, "coin_reward": 4, "type": "daily"},
    # Weekly
    {"id": "weekly_xp", "title": "Weekly Grind", "description": "Earn 500 XP this week", "target": 500, "xp_reward": 200, "coin_reward": 20, "type": "weekly"},
    {"id": "weekly_trophies", "title": "Trophy Hunter", "description": "Unlock 3 trophies this week", "target": 3, "xp_reward": 150, "coin_reward": 15, "type": "weekly"},
    {"id": "weekly_battles", "title": "War Machine", "description": "Complete 5 battles this week", "target": 5, "xp_reward": 150, "coin_reward": 15, "type": "weekly"},
    {"id": "weekly_starmap", "title": "Segmentum Explorer", "description": "Investigate 5 Star Map 25 points this week", "target": 5, "xp_reward": 120, "coin_reward": 12, "type": "weekly"},
    {"id": "weekly_videos", "title": "Content Creator", "description": "Generate 3 videos this week", "target": 3, "xp_reward": 180, "coin_reward": 18, "type": "weekly"},
    {"id": "weekly_social", "title": "Social Week", "description": "Visit Social and Chat 3 times this week", "target": 3, "xp_reward": 80, "coin_reward": 8, "type": "weekly"},
]

WEEKLY_TROPHIES_QUEST_ID = "weekly_trophies"


def _ensure_quest_week_state(user_id: str) -> Dict[str, Any]:
    """Ensure quests.json exists for today/week (no trophy sync)."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    week_start = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).strftime("%Y-%m-%d")
    data = _load(user_id, "quests.json")

    if data.get("date") != today:
        data = {"date": today, "week": week_start, "quests": {}}
        for q in _QUEST_TEMPLATES:
            data["quests"][q["id"]] = {"progress": 0, "completed": False, "claimed": False}
        _save(user_id, "quests.json", data)

    if data.get("week") != week_start:
        for q in _QUEST_TEMPLATES:
            if q["type"] == "weekly":
                data["quests"][q["id"]] = {"progress": 0, "completed": False, "claimed": False}
        data["week"] = week_start
        _save(user_id, "quests.json", data)

    return data


def count_trophy_unlocks_this_week(user_id: str) -> int:
    """Count trophy unlocks since Monday 00:00 UTC (source of truth for weekly_trophies quest)."""
    try:
        from backend.services.trophies_db_service import trophies_tables_exist, _get_db
        if not trophies_tables_exist():
            return 0
        from sqlalchemy import text
        week_start = datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        row = _get_db().session.execute(
            text("""
                SELECT COUNT(*) FROM user_trophy_unlocks
                WHERE user_id = :uid AND unlocked_at >= :week_start
            """),
            {"uid": user_id, "week_start": week_start.isoformat(sep=" ")},
        ).scalar()
        return int(row or 0)
    except Exception:
        return 0


def sync_weekly_trophies_quest(user_id: str) -> Dict[str, Any]:
    """Align weekly_trophies quest progress with DB unlock count for the current week."""
    count = count_trophy_unlocks_this_week(user_id)
    data = _ensure_quest_week_state(user_id)
    state = data.get("quests", {}).get(WEEKLY_TROPHIES_QUEST_ID)
    if not state:
        return {"success": False, "error": "Quest state missing"}
    if state.get("claimed"):
        return {"success": True, "skipped": "claimed", "progress": state.get("progress", 0)}

    template = next((q for q in _QUEST_TEMPLATES if q["id"] == WEEKLY_TROPHIES_QUEST_ID), None)
    if not template:
        return {"success": False, "error": "Unknown quest"}

    target = int(template.get("target", 3))
    new_progress = min(count, target)
    changed = new_progress != int(state.get("progress", 0))
    state["progress"] = new_progress
    state["completed"] = new_progress >= target
    data["quests"][WEEKLY_TROPHIES_QUEST_ID] = state
    if changed:
        _save(user_id, "quests.json", data)
    return {
        "success": True,
        "quest_id": WEEKLY_TROPHIES_QUEST_ID,
        "progress": new_progress,
        "completed": state["completed"],
        "synced_from_db": count,
    }


def on_trophy_unlocked(user_id: str) -> Dict[str, Any]:
    """Called when a trophy is newly unlocked — refreshes weekly_trophies from DB."""
    return sync_weekly_trophies_quest(user_id)


def get_quests(user_id: str) -> Dict[str, Any]:
    """Get current daily/weekly quests with progress."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    week_start = (datetime.utcnow() - timedelta(days=datetime.utcnow().weekday())).strftime("%Y-%m-%d")
    _ensure_quest_week_state(user_id)
    sync_weekly_trophies_quest(user_id)
    data = _load(user_id, "quests.json")

    quests_out = []
    for q in _QUEST_TEMPLATES:
        state = data.get("quests", {}).get(q["id"], {"progress": 0, "completed": False, "claimed": False})
        quests_out.append({**q, **state})
    return {"success": True, "date": today, "week": week_start, "quests": quests_out}


def update_quest_progress(user_id: str, quest_id: str, increment: int = 1) -> Dict[str, Any]:
    """Increment progress on a quest. Auto-completes when target reached."""
    get_quests(user_id)
    data = _load(user_id, "quests.json")
    if not data.get("quests"):
        get_quests(user_id)
        data = _load(user_id, "quests.json")

    state = data.get("quests", {}).get(quest_id)
    if not state:
        return {"success": False, "error": "Quest not found or expired"}

    if state.get("completed"):
        return {"success": True, "already_completed": True}

    template = next((q for q in _QUEST_TEMPLATES if q["id"] == quest_id), None)
    if not template:
        return {"success": False, "error": "Unknown quest"}

    state["progress"] = state.get("progress", 0) + increment
    if state["progress"] >= template["target"]:
        state["completed"] = True
    data["quests"][quest_id] = state
    _save(user_id, "quests.json", data)
    return {"success": True, "quest_id": quest_id, "progress": state["progress"], "completed": state["completed"]}


def claim_quest_reward(user_id: str, quest_id: str) -> Dict[str, Any]:
    """Claim reward for completed quest."""
    data = _load(user_id, "quests.json")
    state = data.get("quests", {}).get(quest_id)
    if not state or not state.get("completed"):
        return {"success": False, "error": "Quest not completed"}
    if state.get("claimed"):
        return {"success": False, "error": "Already claimed"}

    template = next((q for q in _QUEST_TEMPLATES if q["id"] == quest_id), None)
    if not template:
        return {"success": False, "error": "Unknown quest"}

    xp = template.get("xp_reward", 0)
    coins = template.get("coin_reward", 0)
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            if xp > 0:
                unified_points_db.add_points(user_id, "xp_total", xp, source="quest_reward", metadata={"quest_id": quest_id})
                unified_points_db.add_points(user_id, "quest_points", xp, source="quest_reward", metadata={"quest_id": quest_id})
            if coins > 0:
                unified_points_db.add_points(user_id, "coins", coins, source="quest_reward", metadata={"quest_id": quest_id})
    except Exception:
        pass

    state["claimed"] = True
    data["quests"][quest_id] = state
    _save(user_id, "quests.json", data)
    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync('quests')
    except Exception:
        pass
    return {"success": True, "quest_id": quest_id, "xp_awarded": xp, "coins_awarded": coins}


# ============================== NOTIFICATIONS ==============================

def add_notification(user_id: str, title: str, message: str, category: str = "system", metadata: Optional[Dict] = None) -> Dict:
    """Add a notification to user's inbox."""
    data = _load(user_id, "notifications.json")
    if not data.get("items"):
        data = {"items": [], "unread_count": 0}

    notif = {
        "id": f"n_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(data['items'])}",
        "title": title,
        "message": message,
        "category": category,
        "read": False,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    }
    data["items"].insert(0, notif)
    data["items"] = data["items"][:200]
    data["unread_count"] = sum(1 for n in data["items"] if not n.get("read"))
    _save(user_id, "notifications.json", data)
    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync('notifications', count=len(data["items"]))
    except Exception:
        pass
    return notif


def get_notifications(user_id: str, limit: int = 50, unread_only: bool = False) -> Dict[str, Any]:
    data = _load(user_id, "notifications.json")
    items = data.get("items", [])
    if unread_only:
        items = [n for n in items if not n.get("read")]
    return {
        "success": True,
        "notifications": items[:limit],
        "unread_count": sum(1 for n in data.get("items", []) if not n.get("read")),
        "total": len(data.get("items", [])),
    }


def mark_notification_read(user_id: str, notification_id: str) -> Dict[str, Any]:
    data = _load(user_id, "notifications.json")
    for n in data.get("items", []):
        if n.get("id") == notification_id:
            n["read"] = True
            break
    data["unread_count"] = sum(1 for n in data.get("items", []) if not n.get("read"))
    _save(user_id, "notifications.json", data)
    return {"success": True}


def mark_all_read(user_id: str) -> Dict[str, Any]:
    data = _load(user_id, "notifications.json")
    for n in data.get("items", []):
        n["read"] = True
    data["unread_count"] = 0
    _save(user_id, "notifications.json", data)
    return {"success": True}


# ============================== ACHIEVEMENTS / BADGES ==============================

ACHIEVEMENT_DEFS = [
    {"id": "first_video", "title": "First Creation", "description": "Generate your first video", "tier": "bronze", "xp": 50, "check": "generation_points", "threshold": 1},
    {"id": "ten_videos", "title": "Creator", "description": "Generate 10 videos", "tier": "silver", "xp": 200, "check": "generation_points", "threshold": 10},
    {"id": "hundred_videos", "title": "Master Creator", "description": "Generate 100 videos", "tier": "gold", "xp": 1000, "check": "generation_points", "threshold": 100},
    {"id": "first_battle", "title": "First Blood", "description": "Complete your first battle", "tier": "bronze", "xp": 30, "check": "battle_points", "threshold": 1},
    {"id": "battle_veteran", "title": "Battle Veteran", "description": "Earn 100 battle points", "tier": "silver", "xp": 200, "check": "battle_points", "threshold": 100},
    {"id": "battle_legend", "title": "Battle Legend", "description": "Earn 1000 battle points", "tier": "gold", "xp": 1000, "check": "battle_points", "threshold": 1000},
    {"id": "first_theory", "title": "Student", "description": "Study your first theory", "tier": "bronze", "xp": 30, "check": "communication_psychology_points", "threshold": 1},
    {"id": "all_theories", "title": "Psychologist", "description": "Study all 25 theories", "tier": "gold", "xp": 500, "check": "communication_psychology_points", "threshold": 375},
    {"id": "first_trophy", "title": "Collector", "description": "Earn your first trophy", "tier": "bronze", "xp": 30, "check": "trophy_points", "threshold": 1},
    {"id": "trophy_master", "title": "Trophy Master", "description": "Earn 500 trophy points", "tier": "gold", "xp": 500, "check": "trophy_points", "threshold": 500},
    {"id": "reach_level_5", "title": "Rising Star", "description": "Reach level 5", "tier": "bronze", "xp": 100, "check": "level", "threshold": 5},
    {"id": "reach_level_10", "title": "Established", "description": "Reach level 10", "tier": "silver", "xp": 300, "check": "level", "threshold": 10},
    {"id": "reach_level_25", "title": "Elite", "description": "Reach level 25", "tier": "gold", "xp": 1000, "check": "level", "threshold": 25},
    {"id": "week_streak", "title": "Dedicated", "description": "7-day login streak", "tier": "silver", "xp": 150, "check": "streak", "threshold": 7},
    {"id": "month_streak", "title": "Committed", "description": "30-day login streak", "tier": "gold", "xp": 500, "check": "streak", "threshold": 30},
    {"id": "first_purchase", "title": "Shopper", "description": "Make your first shop purchase", "tier": "bronze", "xp": 30, "check": "coins_spent", "threshold": 1},
    {"id": "scholar", "title": "Scholar", "description": "Read all 25 compendium pages", "tier": "gold", "xp": 500, "check": "compendium_pages", "threshold": 25},
    {"id": "rich", "title": "Wealthy", "description": "Accumulate 1000 coins", "tier": "silver", "xp": 200, "check": "coins", "threshold": 1000},
    {"id": "social_butterfly", "title": "Social Butterfly", "description": "Earn 100 social points", "tier": "silver", "xp": 200, "check": "social_points", "threshold": 100},
    {"id": "knowledge_seeker", "title": "Knowledge Seeker", "description": "Earn 200 knowledge points", "tier": "silver", "xp": 200, "check": "knowledge_points", "threshold": 200},
]


def check_achievements(user_id: str, points: Optional[Dict] = None) -> Dict[str, Any]:
    """Check all achievements against current user data. Awards new ones."""
    data = _load(user_id, "achievements.json")
    if not data.get("unlocked"):
        data = {"unlocked": [], "unlocked_ids": []}

    if not points:
        try:
            from backend.services.user_account_summary import get_points
            points = get_points(user_id)
        except Exception:
            points = {}

    streak_data = get_streak(user_id)
    compendium_data = _load(user_id, "compendium_pages.json")

    lookup = {
        **points,
        "streak": streak_data.get("current_streak", 0),
        "compendium_pages": len(compendium_data.get("pages_read", [])),
        "coins_spent": points.get("coins_spent", 0),
    }

    newly_unlocked = []
    for ach in ACHIEVEMENT_DEFS:
        if ach["id"] in data.get("unlocked_ids", []):
            continue
        value = lookup.get(ach["check"], 0)
        if isinstance(value, (int, float)) and value >= ach["threshold"]:
            unlock = {"id": ach["id"], "unlocked_at": datetime.utcnow().isoformat()}
            data["unlocked"].append(unlock)
            data["unlocked_ids"].append(ach["id"])
            newly_unlocked.append(ach)

            try:
                from backend.services.unified_points_database import unified_points_db
                if unified_points_db and ach.get("xp", 0) > 0:
                    unified_points_db.add_points(user_id, "xp_total", ach["xp"], source="achievement",
                                                 metadata={"achievement_id": ach["id"]})
                    unified_points_db.add_points(user_id, "achievements_earned", 1, source="achievement",
                                                 metadata={"achievement_id": ach["id"]})
            except Exception:
                pass
            try:
                from backend.services.unified_points_sync import unified_points_sync_device
                unified_points_sync_device.record_domain_sync('achievements')
            except Exception:
                pass

            add_notification(user_id, f"Achievement Unlocked: {ach['title']}", ach["description"], category="achievement",
                           metadata={"achievement_id": ach["id"], "tier": ach["tier"], "xp": ach["xp"]})

    _save(user_id, "achievements.json", data)
    return {
        "success": True,
        "total_unlocked": len(data["unlocked"]),
        "total_available": len(ACHIEVEMENT_DEFS),
        "newly_unlocked": [a["id"] for a in newly_unlocked],
        "achievements": [
            {**ach, "unlocked": ach["id"] in data.get("unlocked_ids", []),
             "unlocked_at": next((u["unlocked_at"] for u in data["unlocked"] if u["id"] == ach["id"]), None)}
            for ach in ACHIEVEMENT_DEFS
        ],
    }


def get_achievements(user_id: str) -> Dict[str, Any]:
    """Get all achievements with unlock status."""
    data = _load(user_id, "achievements.json")
    unlocked_ids = data.get("unlocked_ids", [])
    return {
        "success": True,
        "total_unlocked": len(unlocked_ids),
        "total_available": len(ACHIEVEMENT_DEFS),
        "achievements": [
            {**ach, "unlocked": ach["id"] in unlocked_ids,
             "unlocked_at": next((u["unlocked_at"] for u in data.get("unlocked", []) if u["id"] == ach["id"]), None)}
            for ach in ACHIEVEMENT_DEFS
        ],
    }


# ============================== COMPENDIUM TRACKING ==============================

def record_compendium_page(user_id: str, page_number: int) -> Dict[str, Any]:
    """Track which compendium pages the user has read."""
    data = _load(user_id, "compendium_pages.json")
    if not data.get("pages_read"):
        data = {"pages_read": [], "total_pages": 25}

    if page_number not in data["pages_read"]:
        data["pages_read"].append(page_number)
        data["pages_read"].sort()
        data["last_read"] = datetime.utcnow().isoformat()
        _save(user_id, "compendium_pages.json", data)

        update_quest_progress(user_id, "read_compendium", increment=1)

    return {
        "success": True,
        "pages_read": data["pages_read"],
        "total_read": len(data["pages_read"]),
        "total_pages": 25,
        "completion_pct": round(len(data["pages_read"]) / 25 * 100, 1),
    }


def get_compendium_progress(user_id: str) -> Dict[str, Any]:
    data = _load(user_id, "compendium_pages.json")
    pages_read = data.get("pages_read", [])
    return {
        "pages_read": pages_read,
        "total_read": len(pages_read),
        "total_pages": 25,
        "completion_pct": round(len(pages_read) / 25 * 100, 1),
    }


# ============================== FAVORITES ==============================

def add_favorite(user_id: str, item_type: str, item_id: str, title: str = "", metadata: Optional[Dict] = None) -> Dict:
    """Add a bookmark/favorite. item_type: video, theory, star, page, etc."""
    data = _load(user_id, "favorites.json")
    if not data.get("items"):
        data = {"items": []}

    key = f"{item_type}:{item_id}"
    existing = next((f for f in data["items"] if f.get("key") == key), None)
    if existing:
        return {"success": True, "already_exists": True, "favorite": existing}

    fav = {
        "key": key,
        "item_type": item_type,
        "item_id": item_id,
        "title": title,
        "created_at": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    }
    data["items"].insert(0, fav)
    _save(user_id, "favorites.json", data)
    return {"success": True, "favorite": fav}


def remove_favorite(user_id: str, item_type: str, item_id: str) -> Dict:
    data = _load(user_id, "favorites.json")
    key = f"{item_type}:{item_id}"
    items = data.get("items", [])
    data["items"] = [f for f in items if f.get("key") != key]
    _save(user_id, "favorites.json", data)
    return {"success": True}


def get_favorites(user_id: str, item_type: Optional[str] = None) -> Dict[str, Any]:
    data = _load(user_id, "favorites.json")
    items = data.get("items", [])
    if item_type:
        items = [f for f in items if f.get("item_type") == item_type]
    return {"success": True, "favorites": items, "total": len(items)}


# ============================== USER SETTINGS ==============================

DEFAULT_SETTINGS = {
    "theme": "dark",
    "language": "en",
    "notifications_enabled": True,
    "email_notifications": False,
    "auto_play_videos": True,
    "default_difficulty": "balanced",
    "show_leaderboard": True,
    "privacy": "public",
    "staking_leaderboard_opt_in": False,
    "staking_display_name": "",
    "staking_show_amounts": False,
}


def get_settings(user_id: str) -> Dict[str, Any]:
    data = _load(user_id, "settings.json")
    settings = {**DEFAULT_SETTINGS}
    if data:
        settings.update(data)
    return {"success": True, "settings": settings}


def update_settings(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    data = _load(user_id, "settings.json")
    if not data:
        data = {**DEFAULT_SETTINGS}
    allowed_keys = set(DEFAULT_SETTINGS.keys())
    for k, v in updates.items():
        if k in allowed_keys:
            data[k] = v
    _save(user_id, "settings.json", data)
    return {"success": True, "settings": data}


# ============================== GENERATION HISTORY ==============================

def get_generation_history(user_id: str, limit: int = 20) -> Dict[str, Any]:
    """Get video generation history for user from generator DB."""
    result = {"jobs": [], "total": 0, "stats": {}}
    try:
        from backend.services.generator_db_service import list_jobs, get_job_statistics, generator_tables_exist
        if generator_tables_exist():
            jobs = list_jobs(user_id=user_id, limit=limit)
            if jobs is not None:
                result["jobs"] = jobs
                result["total"] = len(jobs)
            stats = get_job_statistics(user_id=user_id, days=30)
            if stats:
                result["stats"] = stats
    except Exception:
        pass
    return result
