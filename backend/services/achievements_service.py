"""
Achievements service — loads achievement definitions and evaluates earned status from user progress.
"""
import os
import json
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ACHIEVEMENTS_PATH = os.path.join(BASE_DIR, "data", "achievements.json")
INVESTIGATIONS_PATH = os.path.join(BASE_DIR, "data", "star_map_25_investigations.json")
PROTECTION_PATH = os.path.join(BASE_DIR, "data", "user_password_protection.json")
BUILDUP_PATH = os.path.join(BASE_DIR, "data", "starmap25_buildup.json")


def _load_achievements_definitions() -> List[Dict[str, Any]]:
    if not os.path.exists(ACHIEVEMENTS_PATH):
        return []
    try:
        with open(ACHIEVEMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("achievements", []) or []
    except Exception:
        return []


def _user_investigations_count(user_id: str) -> int:
    if not os.path.exists(INVESTIGATIONS_PATH):
        return 0
    try:
        with open(INVESTIGATIONS_PATH, "r", encoding="utf-8") as f:
            inv = json.load(f)
        return len(inv.get(user_id, []))
    except Exception:
        return 0


def _user_has_password(user_id: str) -> bool:
    if not os.path.exists(PROTECTION_PATH):
        return False
    try:
        with open(PROTECTION_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        user = (data.get("users") or {}).get(user_id, {})
        return bool(user.get("password_hash"))
    except Exception:
        return False


def _user_buildup_collects(user_id: str) -> int:
    """Approximate: 1 if user has ever collected (last_collect_ts set)."""
    if not os.path.exists(BUILDUP_PATH):
        return 0
    try:
        with open(BUILDUP_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        user = (data.get("users") or {}).get(user_id, {})
        return 1 if user.get("last_collect_ts") else 0
    except Exception:
        return 0


def _user_shop_purchases_count(user_id: str) -> int:
    """Try to get purchase count from shop analytics if available."""
    try:
        from backend.services.shop_db_service import get_analytics_user_spending
        out = get_analytics_user_spending(user_id)
        return int(out.get("purchase_count", 0) or 0)
    except Exception:
        pass
    return 0


def _user_friends_and_crew(user_id: str) -> tuple:
    """Return (friends_count, in_crew)."""
    try:
        from backend.routes.social_routes import _load_social
        data = _load_social()
        friends = (data.get("friends") or {}).get(user_id, []) or []
        user_crews = (data.get("user_crews") or {}).get(user_id, []) or []
        return (len(friends), 1 if user_crews else 0)
    except Exception:
        return (0, 0)


def _evaluate_achievement(ach: Dict, context: Dict[str, Any]) -> bool:
    criteria = ach.get("criteria") or {}
    ctype = (criteria.get("type") or "").strip().lower()
    min_val = criteria.get("min", 0)
    if not ctype:
        return False
    if ctype == "level":
        return (context.get("level") or 0) >= min_val
    if ctype == "xp_total":
        return (context.get("xp_total") or 0) >= min_val
    if ctype == "game_points":
        return (context.get("game_points") or 0) >= min_val
    if ctype == "starmap_investigations":
        return (context.get("starmap_investigations") or 0) >= min_val
    if ctype == "battle_points":
        return (context.get("battle_points") or 0) >= min_val
    if ctype == "battles_won":
        return (context.get("battles_won") or 0) >= min_val
    if ctype == "trophies_collected":
        return (context.get("trophies_collected") or 0) >= min_val
    if ctype == "generation_points":
        return (context.get("generation_points") or 0) >= min_val
    if ctype == "achievement_points":
        return (context.get("achievement_points") or 0) >= min_val
    if ctype == "friends_count":
        return (context.get("friends_count") or 0) >= min_val
    if ctype == "in_crew":
        return (context.get("in_crew") or 0) >= min_val
    if ctype == "password_set":
        return bool(context.get("password_set"))
    if ctype == "buildup_collects":
        return (context.get("buildup_collects") or 0) >= min_val
    if ctype == "shop_purchases":
        return (context.get("shop_purchases") or 0) >= min_val
    if ctype == "all_rounder":
        gp = (context.get("game_points") or 0) >= 1
        bp = (context.get("battle_points") or 0) >= 1
        inv = (context.get("starmap_investigations") or 0) >= 1
        return gp and bp and inv
    return False


def get_achievements_with_progress(user_id: str) -> List[Dict[str, Any]]:
    """Load all achievements from data/achievements.json and set earned from user context."""
    definitions = _load_achievements_definitions()
    if not definitions:
        return []

    points_data = {}
    try:
        from backend.services.unified_points_database import unified_points_db
        raw = unified_points_db.get_all_points(user_id)
        if raw and raw.get("success"):
            points_data = raw.get("points", raw) or {}
    except Exception:
        pass

    systems = points_data.get("systems", {})
    level = points_data.get("level", 1)
    xp_total = int(points_data.get("xp_total", 0) or 0)
    game_points = float(systems.get("game_points", 0) or 0)
    battle_points = float(systems.get("battle_points", 0) or 0)
    trophies_collected = int(systems.get("trophies_collected", 0) or 0)
    generation_points = float(systems.get("generation_points", 0) or 0)
    achievement_points = float(systems.get("achievement_points", 0) or 0)
    friends_count, in_crew = _user_friends_and_crew(user_id)

    context = {
        "level": level,
        "xp_total": xp_total,
        "game_points": game_points,
        "battle_points": battle_points,
        "trophies_collected": trophies_collected,
        "generation_points": generation_points,
        "achievement_points": achievement_points,
        "starmap_investigations": _user_investigations_count(user_id),
        "battles_won": 0,
        "friends_count": friends_count,
        "in_crew": in_crew,
        "password_set": _user_has_password(user_id),
        "buildup_collects": _user_buildup_collects(user_id),
        "shop_purchases": _user_shop_purchases_count(user_id),
    }

    result = []
    for ach in definitions:
        earned = _evaluate_achievement(ach, context)
        result.append({
            "id": ach.get("id", ""),
            "name": ach.get("name", ""),
            "description": ach.get("description", ""),
            "icon": ach.get("icon", "🏆"),
            "points": ach.get("points", 0),
            "earned": earned,
        })
    return result
