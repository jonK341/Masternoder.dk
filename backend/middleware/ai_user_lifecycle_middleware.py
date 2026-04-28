"""
AI User Lifecycle Middleware
Runs on every API request to automatically:
  - Detect and classify users (new / returning / dormant / anonymous)
  - Auto-create accounts for unidentified users
  - Record logins and update streaks for returning users
  - Re-engage dormant users with AI nudges
  - Auto-save user state snapshots after meaningful activity
  - Attach lifecycle metadata to Flask g for downstream use
"""
import time
from datetime import datetime, timedelta
from flask import request, session, g

_API_PREFIX = "/api/"
_SAVE_INTERVAL_SECONDS = 300  # snapshot at most every 5 min per user
_DORMANT_DAYS = 7
_last_save_times: dict = {}


def register_ai_user_lifecycle_middleware(app):
    """Register before/after request hooks for the AI user lifecycle."""

    @app.before_request
    def _lifecycle_before():
        if getattr(g, "skip_api_middleware", False):
            return None
        if _API_PREFIX not in request.path:
            return None
        try:
            _detect_and_classify_user()
        except Exception:
            pass

    @app.after_request
    def _lifecycle_after(response):
        if getattr(g, "skip_api_middleware", False):
            return response
        if _API_PREFIX not in request.path:
            return response
        if response.status_code < 400:
            try:
                _auto_save_snapshot()
            except Exception:
                pass
        return response


def _detect_and_classify_user():
    """
    Resolve who the user is and classify their lifecycle stage.
    Stores result in flask.g for use in routes.
    """
    from backend.services.account_resolution_service import resolve_user_id, set_session_user

    user_id = resolve_user_id(from_body=True, from_query=True)
    is_default = (user_id == "default_user")

    # --- Anonymous / new visitor: auto-create an account ---
    if is_default:
        user_id = _auto_create_anonymous_user()
        is_default = (user_id == "default_user")

    g.user_id = user_id
    g.user_is_default = is_default

    if is_default:
        g.user_lifecycle = "anonymous"
        return

    # --- Classify: new / returning / dormant ---
    g.user_lifecycle = _classify_user(user_id)

    # Handle lifecycle event
    lifecycle = g.user_lifecycle

    if lifecycle == "new":
        _handle_new_user(user_id)
    elif lifecycle == "returning":
        _handle_returning_user(user_id)
    elif lifecycle == "dormant":
        _handle_dormant_user(user_id)
    # "active" = already seen today, no special action


def _auto_create_anonymous_user() -> str:
    """
    Attempt to identify or create a user from IP/fingerprint.
    Falls back to 'default_user' if impossible.
    """
    try:
        from backend.services.user_identification import user_identification
        result = user_identification.identify_or_create_user(request)
        if result.get("success") and result.get("user_id"):
            uid = str(result["user_id"]).strip()
            from backend.services.account_resolution_service import set_session_user
            set_session_user(uid)
            return uid
    except Exception:
        pass
    return "default_user"


def _classify_user(user_id: str) -> str:
    """
    Classify user lifecycle stage based on engagement data.
    Returns: 'new' | 'returning' | 'dormant' | 'active'
    """
    try:
        from backend.services.user_engagement import get_streak
        streak = get_streak(user_id)
        last_login = streak.get("last_login")
        total_logins = streak.get("total_logins", 0)
        today = datetime.utcnow().strftime("%Y-%m-%d")

        if total_logins == 0:
            return "new"

        if last_login == today:
            return "active"

        if last_login:
            try:
                last_dt = datetime.strptime(last_login, "%Y-%m-%d")
                days_gone = (datetime.utcnow() - last_dt).days
                if days_gone >= _DORMANT_DAYS:
                    return "dormant"
            except Exception:
                pass

        return "returning"
    except Exception:
        return "new"


def _handle_new_user(user_id: str):
    """First-ever visit. Create DB account + run AI onboarding pipeline."""
    try:
        from backend.services.user_db_service import ensure_user_account, ensure_user_profile
        ensure_user_account(user_id, username=user_id, ip_address=request.remote_addr)
        ensure_user_profile(user_id, username=user_id)
    except Exception:
        pass
    try:
        from backend.services.ai_user_controller import on_user_created
        on_user_created(user_id)
        g.lifecycle_action = "onboarded"
    except Exception:
        pass


def _handle_returning_user(user_id: str):
    """User coming back after absence (< dormant threshold). Update DB + record login + streak."""
    try:
        from backend.services.user_db_service import ensure_user_account, update_lifecycle_stage
        ensure_user_account(user_id, username=user_id, ip_address=request.remote_addr)
        update_lifecycle_stage(user_id, "returning")
    except Exception:
        pass
    try:
        from backend.services.user_engagement import record_login
        login_result = record_login(user_id)
        g.lifecycle_action = "login_recorded"
        g.streak_data = login_result
    except Exception:
        pass


def _handle_dormant_user(user_id: str):
    """
    User hasn't been seen for 7+ days.
    Update DB, record login, send welcome-back notification, apply re-engagement boost.
    """
    try:
        from backend.services.user_db_service import ensure_user_account, update_lifecycle_stage
        ensure_user_account(user_id, username=user_id, ip_address=request.remote_addr)
        update_lifecycle_stage(user_id, "dormant")
    except Exception:
        pass
    try:
        from backend.services.user_engagement import record_login, add_notification, get_streak
        login_result = record_login(user_id)
        g.lifecycle_action = "dormant_reengaged"
        g.streak_data = login_result

        streak = get_streak(user_id)
        days_away = 0
        if streak.get("last_login"):
            try:
                last_dt = datetime.strptime(streak["last_login"], "%Y-%m-%d")
                days_away = (datetime.utcnow() - last_dt).days
            except Exception:
                pass

        add_notification(
            user_id,
            title="Welcome Back, Hunter!",
            message=f"It's been a while! Your streak has reset but your progress is safe. "
                    f"Jump back in — new quests and challenges await.",
            category="welcome_back",
            metadata={"days_away": days_away, "type": "dormant_reengagement"},
        )

        # Re-engagement bonus
        try:
            from backend.services.ai_user_controller import ai_boost_account
            ai_boost_account(user_id, "balanced")
            g.lifecycle_boost = "balanced"
        except Exception:
            pass

        # AI nudge for the return
        try:
            from backend.services.ai_user_controller import generate_engagement_nudge
            nudge = generate_engagement_nudge(user_id)
            if nudge.get("message"):
                add_notification(
                    user_id,
                    title="Your AI Guide Says...",
                    message=nudge["message"],
                    category="ai_guide",
                    metadata={"type": "dormant_nudge"},
                )
        except Exception:
            pass

    except Exception:
        pass


def _auto_save_snapshot():
    """
    Auto-save a lightweight state snapshot after successful API calls.
    Rate-limited to once per 5 minutes per user.
    """
    user_id = getattr(g, "user_id", None)
    if not user_id or user_id == "default_user":
        return

    now = time.time()
    last = _last_save_times.get(user_id, 0)
    if now - last < _SAVE_INTERVAL_SECONDS:
        return

    _last_save_times[user_id] = now

    try:
        from backend.services.ai_user_state_manager import save_user_snapshot
        save_user_snapshot(user_id)
    except Exception:
        pass
