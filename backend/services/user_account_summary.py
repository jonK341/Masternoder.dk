"""
Unified Account Summary
Aggregates all points, progress, and game data for a user into a single payload.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _safe(fn, default=None):
    try:
        return fn()
    except Exception:
        return default


def get_points(user_id: str) -> Dict[str, Any]:
    """All unified points (XP, coins, trophies, etc.)."""
    defaults = {
        "xp_total": 0, "level": 1, "generation_points": 0, "activity_points": 0,
        "battle_points": 0, "quest_points": 0, "game_points": 0,
        "social_points": 0, "knowledge_points": 0,
        "stats_points_total": 0, "stats_points_available": 0,
        "achievements_earned": 0, "milestones_reached": 0,
        "trophy_points": 0, "trophies_collected": 0,
        "coins": 0, "credits": 0,
        # MN2 + game-time fields are part of the unified points contract.
        # They must be present in defaults so file-store fallback preserves them too.
        "mn2_balance": 0,
        "game_time_remaining_minutes": 0,
        "active_boosters": [],
        "dna_manipulation_points": 0, "dna_cloning_points": 0,
        "communication_psychology_points": 0, "compendium_points": 0,
        "systems": {},
    }
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            result = unified_points_db.get_all_points(user_id)
            if result and result.get("success"):
                pts = result.get("points", {})
                if isinstance(pts, dict):
                    defaults.update(pts)
    except Exception:
        pass

    # File fallback
    if defaults["xp_total"] == 0:
        fp = os.path.join(_BASE_DIR, "logs", "unified_points", f"{user_id}.json")
        if os.path.isfile(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    defaults.update({k: v for k, v in data.items() if k in defaults})
            except Exception:
                pass
    return defaults


def get_game_progress(user_id: str) -> Dict[str, Any]:
    """Hunters game level, stats, and XP."""
    progress = {
        "current_level": 1, "current_xp": 0, "total_xp": 0,
        "xp_to_next_level": 1000, "level_progress": 0.0,
        "title": "Novice Hunter", "prestige_level": 0,
        "stats": {"creativity": 0, "efficiency": 0, "quality": 0, "social": 0, "knowledge": 0},
        "available_stat_points": 0,
    }
    try:
        from backend.routes.hunters_game import get_user_level_info
        info = get_user_level_info(user_id)
        if info:
            progress["current_level"] = info.get("current_level", 1)
            progress["current_xp"] = info.get("current_xp", 0)
            progress["total_xp"] = info.get("total_xp", 0)
            progress["xp_to_next_level"] = info.get("xp_to_next_level", 1000)
            progress["level_progress"] = info.get("level_progress", 0.0)
            progress["title"] = info.get("title", "Novice Hunter")
            progress["prestige_level"] = info.get("prestige_level", 0)
            progress["stats"] = {
                "creativity": info.get("stat_creativity", 0),
                "efficiency": info.get("stat_efficiency", 0),
                "quality": info.get("stat_quality", 0),
                "social": info.get("stat_social", 0),
                "knowledge": info.get("stat_knowledge", 0),
            }
            progress["available_stat_points"] = info.get("available_stat_points", 0)
    except Exception:
        pass
    return progress


def get_trophies(user_id: str) -> Dict[str, Any]:
    """Trophy collection summary."""
    result = {"total_unlocked": 0, "trophy_points": 0, "recent": []}
    try:
        from sqlalchemy import text
        from src.db.models import db
        from flask import current_app
        with current_app.app_context():
            rows = db.session.execute(
                text("SELECT trophy_id, unlocked_at FROM user_trophy_unlocks WHERE user_id = :uid ORDER BY unlocked_at DESC LIMIT 10"),
                {"uid": user_id},
            ).fetchall()
            result["total_unlocked"] = len(rows)
            result["recent"] = [{"trophy_id": r[0], "unlocked_at": str(r[1])} for r in rows[:5]]

            count_row = db.session.execute(
                text("SELECT COUNT(*) FROM user_trophy_unlocks WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()
            if count_row:
                result["total_unlocked"] = int(count_row[0])
    except Exception:
        pass
    return result


def get_shop_summary(user_id: str) -> Dict[str, Any]:
    """Shop inventory and purchase count."""
    result = {"total_purchases": 0, "inventory_items": 0, "coins": 0}
    try:
        from sqlalchemy import text
        from src.db.models import db
        from flask import current_app
        with current_app.app_context():
            p = db.session.execute(
                text("SELECT COUNT(*) FROM shop_purchases WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()
            if p:
                result["total_purchases"] = int(p[0])
            i = db.session.execute(
                text("SELECT COALESCE(SUM(quantity),0) FROM user_inventory WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()
            if i:
                result["inventory_items"] = int(i[0])
    except Exception:
        pass
    return result


def get_star_map_25_summary(user_id: str) -> Dict[str, Any]:
    """Star Map 25 investigation progress (connected to profile point systems)."""
    result = {"investigated_count": 0, "total_points": 25, "total_points_earned": 0, "investigated_ids": []}
    try:
        inv_path = os.path.join(_BASE_DIR, "data", "star_map_25_investigations.json")
        if os.path.isfile(inv_path):
            with open(inv_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            result["investigated_ids"] = list(data.get(user_id) or [])
            result["investigated_count"] = len(result["investigated_ids"])
        map_path = os.path.join(_BASE_DIR, "data", "star_map_25.json")
        if os.path.isfile(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                sm = json.load(f)
            points_list = sm.get("points") or []
            point_values = {p.get("id"): p.get("point_value", 10) for p in points_list if p.get("id")}
            result["total_points_earned"] = sum(point_values.get(pid, 10) for pid in result["investigated_ids"])
    except Exception:
        pass
    return result


def get_communication_psychology(user_id: str) -> Dict[str, Any]:
    """Communication psychology progress."""
    result = {"theories_unlocked": 0, "total_theories": 25, "points": 0}
    try:
        from sqlalchemy import text
        from src.db.models import db
        from flask import current_app
        with current_app.app_context():
            row = db.session.execute(
                text("SELECT COUNT(*) FROM comm_psych_theory_unlocks WHERE user_id = :uid"),
                {"uid": user_id},
            ).fetchone()
            if row:
                result["theories_unlocked"] = int(row[0])
    except Exception:
        pass

    # File fallback
    fp = os.path.join(_BASE_DIR, "logs", "communication_psychology", f"{user_id}.json")
    if os.path.isfile(fp):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                data = json.load(f)
            result["theories_unlocked"] = max(
                result["theories_unlocked"],
                len(data.get("unlocked_theories", [])),
            )
            result["points"] = data.get("points", 0)
        except Exception:
            pass
    return result


def get_profile(user_id: str) -> Dict[str, Any]:
    """User profile basics."""
    profile = {"username": user_id, "onboarding_complete": False, "created_at": None}
    try:
        from backend.services.user_onboarding import user_onboarding
        if user_onboarding:
            p = user_onboarding.get_user_profile(user_id)
            if p:
                profile["username"] = p.get("username", user_id)
                profile["onboarding_complete"] = p.get("onboarding_complete", False)
                profile["created_at"] = p.get("created_at")
    except Exception:
        pass
    return profile


def get_battle_summary(user_id: str) -> Dict[str, Any]:
    """Battle stats summary."""
    try:
        from backend.routes.battle_routes import _get_battle_stats
        return _get_battle_stats(user_id)
    except Exception:
        return {"battle_points": 0, "wins": 0, "losses": 0, "total_battles": 0}


def get_generation_history_summary(user_id: str) -> Dict[str, Any]:
    """Generation history summary."""
    try:
        from backend.services.user_engagement import get_generation_history
        return get_generation_history(user_id, limit=5)
    except Exception:
        return {"jobs": [], "total": 0, "stats": {}}


def get_streak_summary(user_id: str) -> Dict[str, Any]:
    """Login streak summary."""
    try:
        from backend.services.user_engagement import get_streak
        return get_streak(user_id)
    except Exception:
        return {"current_streak": 0, "longest_streak": 0, "total_logins": 0}


def get_quest_summary(user_id: str) -> Dict[str, Any]:
    """Active quests summary."""
    try:
        from backend.services.user_engagement import get_quests
        data = get_quests(user_id)
        quests = data.get("quests", [])
        return {
            "active": len([q for q in quests if not q.get("completed")]),
            "completed": len([q for q in quests if q.get("completed")]),
            "total": len(quests),
        }
    except Exception:
        return {"active": 0, "completed": 0, "total": 0}


def get_achievement_summary(user_id: str) -> Dict[str, Any]:
    """Achievements summary."""
    try:
        from backend.services.user_engagement import get_achievements
        data = get_achievements(user_id)
        return {
            "total_unlocked": data.get("total_unlocked", 0),
            "total_available": data.get("total_available", 0),
        }
    except Exception:
        return {"total_unlocked": 0, "total_available": 0}


def get_notification_summary(user_id: str) -> Dict[str, Any]:
    """Notification count."""
    try:
        from backend.services.user_engagement import get_notifications
        data = get_notifications(user_id, limit=1)
        return {"unread_count": data.get("unread_count", 0), "total": data.get("total", 0)}
    except Exception:
        return {"unread_count": 0, "total": 0}


def get_compendium_summary(user_id: str) -> Dict[str, Any]:
    """Compendium reading progress."""
    try:
        from backend.services.user_engagement import get_compendium_progress
        return get_compendium_progress(user_id)
    except Exception:
        return {"total_read": 0, "total_pages": 24, "completion_pct": 0}


def get_favorites_summary(user_id: str) -> Dict[str, Any]:
    """Favorites count."""
    try:
        from backend.services.user_engagement import get_favorites
        data = get_favorites(user_id)
        return {"total": data.get("total", 0)}
    except Exception:
        return {"total": 0}


def get_settings_summary(user_id: str) -> Dict[str, Any]:
    """User settings."""
    try:
        from backend.services.user_engagement import get_settings
        return get_settings(user_id).get("settings", {})
    except Exception:
        return {}


def get_full_account_summary(user_id: str) -> Dict[str, Any]:
    """
    Aggregate ALL points, progress, and account data for a user.
    Returns a single comprehensive payload.
    """
    points = _safe(lambda: get_points(user_id), {})
    game = _safe(lambda: get_game_progress(user_id), {})
    trophies = _safe(lambda: get_trophies(user_id), {})
    shop = _safe(lambda: get_shop_summary(user_id), {})
    star_map_25 = _safe(lambda: get_star_map_25_summary(user_id), {})
    comm_psych = _safe(lambda: get_communication_psychology(user_id), {})
    profile = _safe(lambda: get_profile(user_id), {})
    battle = _safe(lambda: get_battle_summary(user_id), {})
    gen_history = _safe(lambda: get_generation_history_summary(user_id), {})
    streak = _safe(lambda: get_streak_summary(user_id), {})
    quests = _safe(lambda: get_quest_summary(user_id), {})
    achievements = _safe(lambda: get_achievement_summary(user_id), {})
    notifications = _safe(lambda: get_notification_summary(user_id), {})
    compendium = _safe(lambda: get_compendium_summary(user_id), {})
    favorites = _safe(lambda: get_favorites_summary(user_id), {})
    settings = _safe(lambda: get_settings_summary(user_id), {})

    if shop and points:
        shop["coins"] = points.get("coins", 0)

    return {
        "success": True,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        "profile": profile or {},
        "settings": settings or {},
        "points": points or {},
        "game_progress": game or {},
        "star_map_25": star_map_25 or {},
        "battle": battle or {},
        "trophies": trophies or {},
        "achievements": achievements or {},
        "shop": shop or {},
        "communication_psychology": comm_psych or {},
        "compendium": compendium or {},
        "generation_history": gen_history or {},
        "streak": streak or {},
        "quests": quests or {},
        "notifications": notifications or {},
        "favorites": favorites or {},
        "totals": {
            "total_xp": (points or {}).get("xp_total", 0),
            "level": (game or {}).get("current_level", 1),
            "coins": (points or {}).get("coins", 0),
            "trophies_collected": (trophies or {}).get("total_unlocked", 0),
            "achievements_unlocked": (achievements or {}).get("total_unlocked", 0),
            "items_owned": (shop or {}).get("inventory_items", 0),
            "login_streak": (streak or {}).get("current_streak", 0),
            "quests_completed": (quests or {}).get("completed", 0),
            "compendium_read": (compendium or {}).get("total_read", 0),
            "favorites_count": (favorites or {}).get("total", 0),
            "battles_total": (battle or {}).get("total_battles", 0),
            "unread_notifications": (notifications or {}).get("unread_count", 0),
            "star_map_25_investigated": (star_map_25 or {}).get("investigated_count", 0),
            "star_map_25_points_earned": (star_map_25 or {}).get("total_points_earned", 0),
        },
    }
