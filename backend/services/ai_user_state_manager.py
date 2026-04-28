"""
AI User State Manager
Saves and loads complete user state snapshots.
Used by the lifecycle middleware to auto-save and by routes for explicit save/load.
Snapshots stored in logs/user_saves/{user_id}/snapshot.json with history.
"""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SAVES_DIR = os.path.join(_BASE_DIR, "logs", "user_saves")
os.makedirs(_SAVES_DIR, exist_ok=True)

_MAX_HISTORY = 20


def _user_save_dir(user_id: str) -> str:
    d = os.path.join(_SAVES_DIR, user_id)
    os.makedirs(d, exist_ok=True)
    return d


def save_user_snapshot(user_id: str, label: str = "auto") -> Dict[str, Any]:
    """
    Capture a full snapshot of the user's current state across all systems.
    Saves to logs/user_saves/{user_id}/snapshot.json and appends to history.
    """
    snapshot = _build_snapshot(user_id, label)
    save_dir = _user_save_dir(user_id)

    # Write latest snapshot
    snap_path = os.path.join(save_dir, "snapshot.json")
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, default=str)

    # Append to history (ring buffer)
    hist_path = os.path.join(save_dir, "history.json")
    history = []
    if os.path.isfile(hist_path):
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            history = []

    entry = {
        "saved_at": snapshot["saved_at"],
        "label": label,
        "health_score": snapshot.get("health_score", 0),
        "level": snapshot.get("state", {}).get("level", 1),
        "xp": snapshot.get("state", {}).get("xp", 0),
        "coins": snapshot.get("state", {}).get("coins", 0),
        "streak": snapshot.get("state", {}).get("streak", 0),
    }
    history.append(entry)
    history = history[-_MAX_HISTORY:]

    with open(hist_path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str)

    return {"success": True, "user_id": user_id, "label": label, "saved_at": snapshot["saved_at"]}


def load_user_snapshot(user_id: str) -> Dict[str, Any]:
    """Load the latest saved snapshot for a user."""
    snap_path = os.path.join(_user_save_dir(user_id), "snapshot.json")
    if not os.path.isfile(snap_path):
        return {"success": False, "user_id": user_id, "error": "No snapshot found"}
    try:
        with open(snap_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {"success": True, "user_id": user_id, "snapshot": data}
    except Exception as e:
        return {"success": False, "user_id": user_id, "error": str(e)}


def get_save_history(user_id: str) -> Dict[str, Any]:
    """Get the save history (compact entries) for a user."""
    hist_path = os.path.join(_user_save_dir(user_id), "history.json")
    history = []
    if os.path.isfile(hist_path):
        try:
            with open(hist_path, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
    return {"success": True, "user_id": user_id, "total_saves": len(history), "history": history}


def restore_user_state(user_id: str) -> Dict[str, Any]:
    """
    Restore a user's account from their latest snapshot.
    Re-applies points, streak, settings from saved state.
    """
    snap_result = load_user_snapshot(user_id)
    if not snap_result.get("success"):
        return snap_result

    snapshot = snap_result["snapshot"]
    restored = []

    # Restore points
    saved_points = snapshot.get("points", {})
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db and saved_points:
            for ptype in ("xp_points", "coins", "activity_points", "knowledge_points",
                          "battle_points", "social_points", "quest_points"):
                saved_val = saved_points.get(ptype, 0) or saved_points.get(ptype.replace("_points", "_total"), 0)
                if saved_val and saved_val > 0:
                    current = unified_points_db.get_points(user_id, ptype)
                    current_val = current.get("total", 0) if isinstance(current, dict) else 0
                    if saved_val > current_val:
                        diff = saved_val - current_val
                        unified_points_db.add_points(user_id, ptype, diff, source="state_restore")
                        restored.append(f"Restored {diff} {ptype}")
    except Exception:
        pass

    # Restore settings
    saved_settings = snapshot.get("settings", {})
    if saved_settings:
        try:
            from backend.services.user_engagement import update_settings
            update_settings(user_id, saved_settings)
            restored.append("Settings restored")
        except Exception:
            pass

    # Restore favorites
    saved_favs = snapshot.get("favorites", {})
    if saved_favs.get("items"):
        try:
            from backend.services.user_engagement import add_favorite
            for fav in saved_favs["items"][:20]:
                add_favorite(user_id, fav.get("item_type", "unknown"), fav.get("item_id", ""),
                             title=fav.get("title", ""), metadata=fav.get("metadata"))
            restored.append(f"Favorites restored ({len(saved_favs['items'])} items)")
        except Exception:
            pass

    return {
        "success": True,
        "user_id": user_id,
        "restored_from": snapshot.get("saved_at"),
        "actions": restored,
        "total_restored": len(restored),
    }


def _build_snapshot(user_id: str, label: str = "auto") -> Dict[str, Any]:
    """Build a full state snapshot by pulling from all services."""
    snapshot = {
        "user_id": user_id,
        "saved_at": datetime.utcnow().isoformat(),
        "label": label,
        "state": {},
        "points": {},
        "profile": {},
        "streak": {},
        "quests": {},
        "achievements": {},
        "notifications_count": 0,
        "compendium": {},
        "favorites": {},
        "settings": {},
        "battle": {},
        "health_score": 0,
    }

    # State (from AI controller)
    try:
        from backend.services.ai_user_controller import _gather_user_state
        snapshot["state"] = _gather_user_state(user_id)
    except Exception:
        pass

    # Points
    try:
        from backend.services.user_account_summary import get_points
        snapshot["points"] = get_points(user_id)
    except Exception:
        pass

    # Profile
    try:
        from backend.services.user_account_summary import get_profile
        snapshot["profile"] = get_profile(user_id)
    except Exception:
        pass

    # Streak
    try:
        from backend.services.user_engagement import get_streak
        snapshot["streak"] = get_streak(user_id)
    except Exception:
        pass

    # Quests
    try:
        from backend.services.user_engagement import get_quests
        snapshot["quests"] = get_quests(user_id)
    except Exception:
        pass

    # Achievements
    try:
        from backend.services.user_engagement import get_achievements
        snapshot["achievements"] = get_achievements(user_id)
    except Exception:
        pass

    # Notifications count
    try:
        from backend.services.user_engagement import get_notifications
        notifs = get_notifications(user_id, limit=1, unread_only=True)
        snapshot["notifications_count"] = notifs.get("unread_count", 0)
    except Exception:
        pass

    # Compendium
    try:
        from backend.services.user_engagement import get_compendium_progress
        snapshot["compendium"] = get_compendium_progress(user_id)
    except Exception:
        pass

    # Favorites
    try:
        from backend.services.user_engagement import get_favorites
        snapshot["favorites"] = get_favorites(user_id)
    except Exception:
        pass

    # Settings
    try:
        from backend.services.user_engagement import get_settings
        snapshot["settings"] = get_settings(user_id)
    except Exception:
        pass

    # Battle
    try:
        from backend.services.user_account_summary import get_battle_summary
        snapshot["battle"] = get_battle_summary(user_id)
    except Exception:
        pass

    # Health score
    try:
        from backend.services.ai_user_controller import account_health_check
        health = account_health_check(user_id)
        snapshot["health_score"] = health.get("health_score", 0)
    except Exception:
        pass

    return snapshot


def classify_user(user_id: str) -> Dict[str, Any]:
    """
    Classify a user's lifecycle stage with full detail.
    Returns classification, days since last visit, total visits, and recommended action.
    """
    try:
        from backend.services.user_engagement import get_streak
        streak = get_streak(user_id)
    except Exception:
        streak = {}

    total_logins = streak.get("total_logins", 0)
    last_login = streak.get("last_login")
    current_streak = streak.get("current_streak", 0)
    today = datetime.utcnow().strftime("%Y-%m-%d")

    days_away = 0
    if last_login and last_login != today:
        try:
            last_dt = datetime.strptime(last_login, "%Y-%m-%d")
            days_away = (datetime.utcnow() - last_dt).days
        except Exception:
            pass

    if total_logins == 0:
        classification = "new"
        recommended_action = "Run full AI onboarding: POST /api/user/ai/build"
    elif last_login == today:
        classification = "active"
        recommended_action = "Check quests and achievements: GET /api/user/quests"
    elif days_away >= 30:
        classification = "churned"
        recommended_action = "Run account repair + boost: POST /api/user/ai/repair then /ai/boost"
    elif days_away >= 7:
        classification = "dormant"
        recommended_action = "Welcome back flow + balanced boost: POST /api/user/ai/boost"
    else:
        classification = "returning"
        recommended_action = "Record login + check streaks: POST /api/user/streak/login"

    # Check if account has a saved snapshot
    snap_path = os.path.join(_user_save_dir(user_id), "snapshot.json")
    has_save = os.path.isfile(snap_path)

    return {
        "success": True,
        "user_id": user_id,
        "classification": classification,
        "days_since_last_visit": days_away,
        "total_logins": total_logins,
        "current_streak": current_streak,
        "has_saved_state": has_save,
        "recommended_action": recommended_action,
    }
