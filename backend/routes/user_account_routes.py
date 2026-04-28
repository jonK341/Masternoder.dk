"""
User account control — user index and ID for generation and account UI.
Provides stable user_id and user_index for use in generator context and account control.
Includes /api/user/account-summary that aggregates ALL points and progress.
Includes AI controller endpoints for automated user management.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request
from backend.services.account_resolution_service import resolve_user_id, resolve_user_id_with_source
from backend.services import ai_user_controller

user_account_bp = Blueprint("user_account", __name__)


def _resolve(allow_default: bool = True) -> str:
    """Resolve user_id via session > query > identification. Falls back to 'default_user'."""
    uid = resolve_user_id(from_body=True, from_query=True)
    if not allow_default and uid == "default_user":
        return ""
    return uid


def _user_index_from_id(user_id: str) -> int:
    """Derive a stable numeric index from user_id (0–999999)."""
    if not user_id:
        return 0
    h = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return int(h[:8], 16) % 1000000


def _parse_profile_preferences(profile: dict | None) -> dict:
    """Return profile preferences as a dict regardless of DB/file storage format."""
    if not profile:
        return {}
    raw = profile.get("preferences") or {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _update_profile_preferences(user_id: str, updates: dict) -> dict:
    """Merge updates into profile.preferences using the existing profile service."""
    from backend.services.user_onboarding import user_onboarding

    profile = user_onboarding.get_user_profile(user_id)
    if not profile:
        created = user_onboarding.create_new_user(
            {
                "user_agent": request.headers.get("User-Agent", ""),
                "ip_address": request.remote_addr,
                "language": request.headers.get("Accept-Language", ""),
                "referral_source": "account_controls",
                "preferences": {},
            },
            user_id,
        )
        if not created.get("success"):
            return created
        profile = user_onboarding.get_user_profile(user_id)

    prefs = _parse_profile_preferences(profile)
    prefs.update(updates)
    return user_onboarding.update_user_profile(user_id, {"preferences": prefs})


def _current_session_payload(user_id: str, resolution_source: str) -> dict:
    """Build a sanitized persistent session/device entry for the current request."""
    from backend.services.account_session_service import build_current_session
    return build_current_session(user_id, resolution_source, request.headers.get("User-Agent", ""), request.remote_addr or "")


def _record_current_session(user_id: str, resolution_source: str) -> list[dict]:
    """Persist and return recent session/device entries in profile preferences."""
    try:
        from backend.services.account_session_service import record_current_session
        return record_current_session(user_id, resolution_source, request.headers.get("User-Agent", ""), request.remote_addr or "")
    except Exception:
        return [_current_session_payload(user_id, resolution_source)]


def _build_top5_account_control(user_id: str) -> dict:
    """Build top-5 control payload for user account management."""
    top5 = {
        "top_agents_by_assigned_skills": [],
        "top_unique_skills_by_value": [],
        "top_battle_agents_by_power": [],
        "top_actions": [
            {"label": "Provision Full Access", "api": "/api/user/provision/full-access", "method": "POST"},
            {"label": "Rebalance Unique Skill Values", "api": "/api/agents/skillsets/rebalance", "method": "POST"},
            {"label": "Ensure Battle Skills", "api": "/api/agents/skillsets/battle/ensure", "method": "POST"},
            {"label": "Ensure Sales Skills", "api": "/api/agents/skillsets/sales/ensure", "method": "POST"},
            {"label": "Ensure Shared Growth Skills", "api": "/api/agents/skillsets/shared-growth/ensure", "method": "POST"},
            {"label": "Ensure Blueprint/Route Fixer Skills", "api": "/api/agents/skillsets/blueprint-route-fixer/ensure", "method": "POST"},
            {"label": "Ensure API Service Skills", "api": "/api/agents/skillsets/api-service/ensure", "method": "POST"},
        ],
    }

    try:
        from backend.services.user_agent_skills import user_agent_skills
        from backend.services.agent_skillset import agent_skillset

        user_skills = user_agent_skills.get_user_skills(user_id) or {}
        all_agents = (agent_skillset.get_all_skillsets() or {}).get("agents", {}) or {}

        # Top agents by user-assigned skills
        counts = {}
        for s in user_skills.get("skills", []):
            agent_id = s.get("agent_id")
            if not agent_id:
                continue
            counts[agent_id] = counts.get(agent_id, 0) + 1
        ranked_agents = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top5["top_agents_by_assigned_skills"] = [
            {
                "agent_id": aid,
                "agent_name": (all_agents.get(aid) or {}).get("name", aid),
                "assigned_skills": c,
            }
            for aid, c in ranked_agents
        ]

        # Top unique skills by value across assigned agents
        assigned_ids = set(user_skills.get("assigned_agents", []))
        all_unique = []
        for aid in assigned_ids:
            agent = all_agents.get(aid) or {}
            for p in agent.get("unique_skill_profiles", []):
                all_unique.append({
                    "agent_id": aid,
                    "skill_name": p.get("skill_name"),
                    "value_points": int(p.get("value_points", 0)),
                })
        top5["top_unique_skills_by_value"] = sorted(
            all_unique, key=lambda x: x["value_points"], reverse=True
        )[:5]

        # Top battle agents by battle skill power
        battle_rank = []
        for aid in assigned_ids:
            agent = all_agents.get(aid) or {}
            battle_rank.append({
                "agent_id": aid,
                "agent_name": agent.get("name", aid),
                "battle_skill_power_total": int(agent.get("battle_skill_power_total", 0)),
            })
        top5["top_battle_agents_by_power"] = sorted(
            battle_rank, key=lambda x: x["battle_skill_power_total"], reverse=True
        )[:5]
    except Exception:
        pass

    return top5


@user_account_bp.route("/api/user/index", methods=["GET"])
@user_account_bp.route("/api/users/me", methods=["GET"])
def user_index_and_id():
    """
    Return current user's ID and index for account control and generation.
    Uses session-based resolution first, then query param fallback.
    """
    user_id = _resolve()
    user_index = _user_index_from_id(user_id)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "user_index": user_index,
        "message": "Use user_id and user_index for account control and generation context.",
    }), 200


@user_account_bp.route("/api/user/account-control", methods=["GET"])
def account_control_context():
    """
    Return context for user account control generation: user_id, user_index, and optional profile summary.
    Generator or frontend can use this to personalize content or enforce user-scoped actions.
    """
    user_id = _resolve()
    user_index = _user_index_from_id(user_id)
    try:
        from backend.services.user_onboarding import user_onboarding
        profile = user_onboarding.get_user_profile(user_id) if user_onboarding else None
    except Exception:
        profile = None
    # AI account health (fast, no LLM)
    try:
        ai_health_data = ai_user_controller.account_health_check(user_id)
        ai_control = {
            "health_score": ai_health_data.get("health_score", 0),
            "health_grade": ai_health_data.get("health_grade", "?"),
            "issues": ai_health_data.get("total_issues", 0),
            "repairs_available": len(ai_health_data.get("repairs_available", [])),
            "managed_by": "AI User Controller v2",
        }
    except Exception:
        ai_control = {"managed_by": "AI User Controller v2", "health_score": 0}

    return jsonify({
        "success": True,
        "user_id": user_id,
        "user_index": user_index,
        "top5_account_control": _build_top5_account_control(user_id),
        "ai_control": ai_control,
        "profile": {
            "username": profile.get("username") if profile else user_id,
            "onboarding_complete": profile.get("onboarding_complete", False) if profile else False,
        } if profile else {"username": user_id, "onboarding_complete": False},
    }), 200


@user_account_bp.route("/api/user/account-control/top5", methods=["GET"])
def account_control_top5():
    """Return top-5 user account controls and rankings."""
    user_id = _resolve()
    return jsonify({
        "success": True,
        "user_id": user_id,
        "top5_account_control": _build_top5_account_control(user_id),
    }), 200


@user_account_bp.route("/api/user/identity", methods=["GET"])
def user_identity_full():
    """
    Return full user identity and account data for the profile: user_id, resolution source,
    session state, stored identifiers (sanitized), and where progress is stored.
    """
    user_id, resolution_source = resolve_user_id_with_source(from_body=True, from_query=True)
    user_index = _user_index_from_id(user_id)
    session_bound = resolution_source == "session"

    # Stored identifiers (sanitized for client: no raw IP, fingerprint truncated)
    identifiers_display = {}
    try:
        from backend.services.user_identification import user_identification
        raw = user_identification.get_identifiers_for_user(user_id)
        if raw:
            identifiers_display = {
                "ip_hash": raw.get("ip_address", "—")[:8] + "…" if raw.get("ip_address") else None,
                "fingerprint_present": bool(raw.get("composite_fingerprint")),
                "user_agent_preview": (raw.get("user_agent") or "")[:60] + "…" if raw.get("user_agent") else None,
                "language": raw.get("accept_language"),
                "timestamp": raw.get("timestamp"),
            }
            identifiers_display = {k: v for k, v in identifiers_display.items() if v is not None}
    except Exception:
        pass

    # Where progress is stored (all keyed by user_id)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    progress_stores = [
        {"name": "Unified points", "key": "user_id", "path": f"logs/unified_points/{user_id}.json"},
        {"name": "Star Map 25 investigations", "key": "user_id", "path": "data/star_map_25_investigations.json"},
        {"name": "Player level / XP", "key": "user_id", "backend": "player_levels"},
        {"name": "Trophies", "key": "user_id", "backend": "user_trophy_unlocks"},
        {"name": "Shop / inventory", "key": "user_id", "backend": "shop_purchases, user_inventory"},
    ]
    # Check if points file exists
    try:
        up_path = os.path.join(base_dir, "logs", "unified_points", f"{user_id}.json")
        progress_stores[0]["exists"] = os.path.isfile(up_path)
    except Exception:
        progress_stores[0]["exists"] = False

    profile = None
    preferences = {}
    try:
        from backend.services.user_onboarding import user_onboarding
        profile = user_onboarding.get_user_profile(user_id)
        preferences = _parse_profile_preferences(profile)
    except Exception:
        profile = None
        preferences = {}

    linked_providers = preferences.get("linked_providers") or []
    if not isinstance(linked_providers, list):
        linked_providers = []

    return jsonify({
        "success": True,
        "user_id": user_id,
        "user_index": user_index,
        "session_bound": session_bound,
        "resolution_source": resolution_source,
        "identity_model": {
            "anonymous_device_id": identifiers_display.get("ip_hash") or f"browser:{user_index}",
            "authenticated_user_id": user_id if session_bound else None,
            "display_name": preferences.get("display_name") or (profile or {}).get("username") or user_id,
            "linked_providers": linked_providers,
        },
        "identifiers": identifiers_display,
        "progress_stores": progress_stores,
    }), 200


@user_account_bp.route("/api/user/account-privacy", methods=["GET", "POST"])
def user_account_privacy():
    """Get or update profile privacy, notification, language, and feature preferences."""
    user_id = _resolve()
    from backend.services.user_engagement import get_settings, update_settings

    if request.method == "GET":
        profile = None
        try:
            from backend.services.user_onboarding import user_onboarding
            profile = user_onboarding.get_user_profile(user_id)
        except Exception:
            profile = None
        prefs = _parse_profile_preferences(profile)
        settings = (get_settings(user_id) or {}).get("settings", {})
        linked = prefs.get("linked_providers") or []
        if not isinstance(linked, list):
            linked = []
        return jsonify({
            "success": True,
            "user_id": user_id,
            "privacy": {
                "profile_visibility": prefs.get("profile_visibility") or settings.get("privacy") or "public",
                "preferred_language": prefs.get("preferred_language") or settings.get("language") or "en",
                "notifications_enabled": bool(prefs.get("notifications_enabled", settings.get("notifications_enabled", True))),
                "email_notifications": bool(prefs.get("email_notifications", settings.get("email_notifications", False))),
                "featured_achievement": prefs.get("featured_achievement") or "",
                "pinned_activity": prefs.get("pinned_activity") or "",
                "featured_agents": prefs.get("featured_agents") if isinstance(prefs.get("featured_agents"), list) else [],
                "profile_theme": prefs.get("profile_theme") or settings.get("theme") or "dark",
                "linked_providers": linked,
                "account_deleted": bool(prefs.get("account_deleted", False)),
            },
        }), 200

    data = request.get_json() or {}
    allowed_visibility = {"public", "private", "friends"}
    allowed_theme = {"dark", "neon", "minimal", "system"}
    visibility = str(data.get("profile_visibility") or "public").strip().lower()
    language = str(data.get("preferred_language") or "en").strip()[:12] or "en"
    theme = str(data.get("profile_theme") or "dark").strip().lower()
    if visibility not in allowed_visibility:
        return jsonify({"success": False, "error": "profile_visibility must be public, private, or friends"}), 400
    if theme not in allowed_theme:
        return jsonify({"success": False, "error": "profile_theme must be dark, neon, minimal, or system"}), 400

    featured_agents = data.get("featured_agents")
    if isinstance(featured_agents, str):
        featured_agents = [x.strip() for x in featured_agents.split(",") if x.strip()]
    if not isinstance(featured_agents, list):
        featured_agents = []

    updates = {
        "profile_visibility": visibility,
        "preferred_language": language,
        "notifications_enabled": bool(data.get("notifications_enabled", True)),
        "email_notifications": bool(data.get("email_notifications", False)),
        "featured_achievement": str(data.get("featured_achievement") or "").strip()[:120],
        "pinned_activity": str(data.get("pinned_activity") or "").strip()[:200],
        "featured_agents": featured_agents[:5],
        "profile_theme": theme,
        "privacy_updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = _update_profile_preferences(user_id, updates)
    update_settings(user_id, {
        "privacy": visibility,
        "language": language,
        "notifications_enabled": updates["notifications_enabled"],
        "email_notifications": updates["email_notifications"],
        "theme": theme,
    })
    return jsonify({"success": bool(result.get("success")), "user_id": user_id, "privacy": updates, "profile_result": result}), 200 if result.get("success") else 400


@user_account_bp.route("/api/user/export", methods=["GET"])
def user_account_export():
    """Export the user's account/profile state as JSON."""
    user_id = _resolve()
    export = {"success": True, "user_id": user_id, "exported_at": datetime.now(timezone.utc).isoformat()}
    try:
        from backend.services.user_onboarding import user_onboarding
        export["profile"] = user_onboarding.get_user_profile(user_id) or {}
    except Exception as e:
        export["profile_error"] = str(e)
    try:
        from backend.services.user_engagement import get_settings
        export["settings"] = (get_settings(user_id) or {}).get("settings", {})
    except Exception as e:
        export["settings_error"] = str(e)
    try:
        from backend.services.user_account_summary import get_full_account_summary
        export["account_summary"] = get_full_account_summary(user_id)
    except Exception as e:
        export["account_summary_error"] = str(e)
    return jsonify(export), 200


@user_account_bp.route("/api/user/delete", methods=["POST"])
def user_account_delete():
    """Soft-delete an account by hiding profile data and disabling outward-facing preferences."""
    user_id = _resolve()
    data = request.get_json() or {}
    if data.get("confirm") != "DELETE":
        return jsonify({"success": False, "error": "confirm must equal DELETE"}), 400
    updates = {
        "account_deleted": True,
        "profile_visibility": "private",
        "notifications_enabled": False,
        "email_notifications": False,
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }
    result = _update_profile_preferences(user_id, updates)
    try:
        from backend.services.user_engagement import update_settings
        update_settings(user_id, {"privacy": "private", "notifications_enabled": False, "email_notifications": False})
    except Exception:
        pass
    return jsonify({"success": bool(result.get("success")), "user_id": user_id, "deleted": bool(result.get("success")), "mode": "soft_delete", "profile_result": result}), 200 if result.get("success") else 400


@user_account_bp.route("/api/user/linked-providers", methods=["GET", "POST"])
def user_linked_providers():
    """List configured social providers and manage profile-linked provider labels."""
    user_id = _resolve()
    try:
        from backend.services.social_auth_service import list_providers
        configured = list_providers().get("providers", [])
    except Exception:
        configured = []

    profile = None
    try:
        from backend.services.user_onboarding import user_onboarding
        profile = user_onboarding.get_user_profile(user_id)
    except Exception:
        profile = None
    prefs = _parse_profile_preferences(profile)
    linked = prefs.get("linked_providers") or []
    if not isinstance(linked, list):
        linked = []

    if request.method == "GET":
        try:
            from backend.services.social_auth_service import oauth_token_storage_enabled
            token_store_supported = oauth_token_storage_enabled()
        except Exception:
            token_store_supported = False
        provider_status = [
            {
                "id": p.get("id") if isinstance(p, dict) else str(p),
                "configured": bool((p or {}).get("configured", False)) if isinstance(p, dict) else False,
                "linked": (p.get("id") if isinstance(p, dict) else str(p)) in linked,
                "revocation_supported": token_store_supported,
            }
            for p in (configured or [{"id": "github"}, {"id": "google"}])
        ]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "configured_providers": configured,
            "linked_providers": linked,
            "providers": provider_status,
            "revocation_supported": token_store_supported,
            "revocation_note": "Provider tokens can be revoked when SOCIAL_AUTH_STORE_TOKENS is enabled." if token_store_supported else "Provider disconnect is local-only until OAuth token storage is enabled.",
        }), 200

    data = request.get_json() or {}
    provider = str(data.get("provider") or "").strip().lower()
    action = str(data.get("action") or "unlink").strip().lower()
    allowed = {p.get("id") for p in configured if isinstance(p, dict) and p.get("id")} | {"github", "google"}
    if provider not in allowed:
        return jsonify({"success": False, "error": "unknown provider"}), 400
    revocation = {"success": False, "revocation_supported": False, "error": "not requested"}
    if action == "link":
        if provider not in linked:
            linked.append(provider)
    elif action == "unlink":
        try:
            from backend.services.social_auth_service import revoke_oauth_provider
            revocation = revoke_oauth_provider(user_id, provider)
        except Exception as e:
            revocation = {"success": False, "revocation_supported": False, "error": str(e)}
        linked = [p for p in linked if p != provider]
    else:
        return jsonify({"success": False, "error": "action must be link or unlink"}), 400
    result = _update_profile_preferences(user_id, {
        "linked_providers": linked,
        "linked_providers_updated_at": datetime.now(timezone.utc).isoformat(),
        "last_provider_disconnect": {
            "provider": provider,
            "action": action,
            "revocation_status": "provider_revoked" if revocation.get("success") else "local_only",
            "message": "Provider token revoked and local link updated." if revocation.get("success") else f"Local profile link updated. {revocation.get('error') or 'Provider token revocation unavailable.'}",
            "at": datetime.now(timezone.utc).isoformat(),
        },
    })
    return jsonify({
        "success": bool(result.get("success")),
        "user_id": user_id,
        "linked_providers": linked,
        "revocation_status": "provider_revoked" if revocation.get("success") else "local_only",
        "revocation_supported": bool(revocation.get("revocation_supported")),
        "revocation": revocation,
    }), 200 if result.get("success") else 400


@user_account_bp.route("/api/user/sessions", methods=["GET"])
def user_sessions():
    """Return persistent session/device identity details for account UI."""
    user_id, resolution_source = resolve_user_id_with_source(from_body=True, from_query=True)
    sessions = _record_current_session(user_id, resolution_source)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "persistent": True,
        "sessions": sessions,
    }), 200


@user_account_bp.route("/api/user/sessions/revoke", methods=["POST"])
def user_session_revoke():
    """Mark a persisted non-current session/device as revoked."""
    user_id = _resolve()
    data = request.get_json() or {}
    session_id = str(data.get("session_id") or "").strip()
    if not session_id:
        return jsonify({"success": False, "error": "session_id required"}), 400
    try:
        from backend.services.account_session_service import current_session_id, revoke_session
        current_id = current_session_id(user_id, request.headers.get("User-Agent", ""), request.remote_addr or "")
        result = revoke_session(user_id, session_id, current_id)
        status = 200 if result.get("success") else (400 if "current" in str(result.get("error")) else 404)
        return jsonify(result), status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== UNIFIED ACCOUNT SUMMARY ====================

@user_account_bp.route("/api/user/account-summary", methods=["GET"])
def account_summary():
    """
    Return ALL points, progress, trophies, shop, and game data for a user.
    Single comprehensive payload that ties everything to the user account.
    """
    user_id = _resolve()
    try:
        from backend.services.user_account_summary import get_full_account_summary
        return jsonify(get_full_account_summary(user_id)), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "user_id": user_id,
            "error": str(e),
            "message": "Account summary unavailable; partial data returned.",
            "points": {}, "game_progress": {}, "trophies": {},
            "shop": {}, "communication_psychology": {},
        }), 200


@user_account_bp.route("/api/user/account-summary/points", methods=["GET"])
def account_summary_points():
    """Return only the points section of the account summary."""
    user_id = _resolve()
    try:
        from backend.services.user_account_summary import get_points
        return jsonify({"success": True, "user_id": user_id, "points": get_points(user_id)}), 200
    except Exception as e:
        return jsonify({"success": False, "user_id": user_id, "error": str(e), "points": {}}), 200


@user_account_bp.route("/api/user/account-summary/progress", methods=["GET"])
def account_summary_progress():
    """Return game progress + communication psychology for a user."""
    user_id = _resolve()
    try:
        from backend.services.user_account_summary import get_game_progress, get_communication_psychology
        return jsonify({
            "success": True, "user_id": user_id,
            "game_progress": get_game_progress(user_id),
            "communication_psychology": get_communication_psychology(user_id),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "user_id": user_id, "error": str(e)}), 200


# ==================== LOGIN STREAK ====================

@user_account_bp.route("/api/user/streak", methods=["GET"])
def user_streak():
    """Get login streak info."""
    user_id = _resolve()
    from backend.services.user_engagement import get_streak
    return jsonify({"success": True, "user_id": user_id, **get_streak(user_id)}), 200


@user_account_bp.route("/api/user/streak/login", methods=["POST"])
def user_streak_login():
    """Record a login for streak tracking."""
    user_id = _resolve()
    from backend.services.user_engagement import record_login
    return jsonify({"success": True, "user_id": user_id, **record_login(user_id)}), 200


# ==================== QUESTS ====================

@user_account_bp.route("/api/user/quests", methods=["GET"])
def user_quests():
    """Get daily/weekly quests with progress."""
    user_id = _resolve()
    from backend.services.user_engagement import get_quests
    return jsonify(get_quests(user_id)), 200


@user_account_bp.route("/api/user/quests/progress", methods=["POST"])
def user_quest_progress():
    """Update quest progress."""
    user_id = _resolve()
    data = request.get_json() or {}
    quest_id = data.get("quest_id", "")
    increment = int(data.get("increment", 1))
    if not quest_id:
        return jsonify({"success": False, "error": "quest_id required"}), 400
    from backend.services.user_engagement import update_quest_progress
    return jsonify(update_quest_progress(user_id, quest_id, increment)), 200


@user_account_bp.route("/api/user/quests/claim", methods=["POST"])
def user_quest_claim():
    """Claim reward for completed quest."""
    user_id = _resolve()
    data = request.get_json() or {}
    quest_id = data.get("quest_id", "")
    if not quest_id:
        return jsonify({"success": False, "error": "quest_id required"}), 400
    from backend.services.user_engagement import claim_quest_reward
    return jsonify(claim_quest_reward(user_id, quest_id)), 200


# ==================== NOTIFICATIONS ====================

@user_account_bp.route("/api/user/notifications", methods=["GET"])
def user_notifications():
    """Get notifications inbox."""
    user_id = _resolve()
    limit = min(100, int(request.args.get("limit", 50)))
    unread_only = request.args.get("unread_only", "").lower() in ("1", "true", "yes")
    from backend.services.user_engagement import get_notifications
    return jsonify(get_notifications(user_id, limit=limit, unread_only=unread_only)), 200


@user_account_bp.route("/api/user/notifications/read", methods=["POST"])
def user_notification_read():
    """Mark a notification as read."""
    user_id = _resolve()
    data = request.get_json() or {}
    nid = data.get("notification_id", "")
    if nid == "all":
        from backend.services.user_engagement import mark_all_read
        return jsonify(mark_all_read(user_id)), 200
    if not nid:
        return jsonify({"success": False, "error": "notification_id required"}), 400
    from backend.services.user_engagement import mark_notification_read
    return jsonify(mark_notification_read(user_id, nid)), 200


# ==================== ACHIEVEMENTS ====================

@user_account_bp.route("/api/user/achievements", methods=["GET"])
def user_achievements():
    """Get all achievements with unlock status."""
    user_id = _resolve()
    from backend.services.user_engagement import get_achievements
    return jsonify(get_achievements(user_id)), 200


@user_account_bp.route("/api/user/achievements/check", methods=["POST"])
def user_achievements_check():
    """Check and award new achievements based on current data."""
    user_id = _resolve()
    from backend.services.user_engagement import check_achievements
    return jsonify(check_achievements(user_id)), 200


# ==================== COMPENDIUM PROGRESS ====================

@user_account_bp.route("/api/user/compendium/progress", methods=["GET"])
def user_compendium_progress():
    """Get compendium reading progress."""
    user_id = _resolve()
    from backend.services.user_engagement import get_compendium_progress
    return jsonify({"success": True, "user_id": user_id, **get_compendium_progress(user_id)}), 200


# ==================== FAVORITES ====================

@user_account_bp.route("/api/user/favorites", methods=["GET"])
def user_favorites():
    """Get user's favorites/bookmarks."""
    user_id = _resolve()
    item_type = request.args.get("type")
    from backend.services.user_engagement import get_favorites
    return jsonify(get_favorites(user_id, item_type=item_type)), 200


@user_account_bp.route("/api/user/favorites/add", methods=["POST"])
def user_favorite_add():
    """Add a favorite."""
    user_id = _resolve()
    data = request.get_json() or {}
    item_type = data.get("item_type", "")
    item_id = data.get("item_id", "")
    if not item_type or not item_id:
        return jsonify({"success": False, "error": "item_type and item_id required"}), 400
    from backend.services.user_engagement import add_favorite
    return jsonify(add_favorite(user_id, item_type, item_id, title=data.get("title", ""), metadata=data.get("metadata"))), 200


@user_account_bp.route("/api/user/favorites/remove", methods=["POST"])
def user_favorite_remove():
    """Remove a favorite."""
    user_id = _resolve()
    data = request.get_json() or {}
    item_type = data.get("item_type", "")
    item_id = data.get("item_id", "")
    if not item_type or not item_id:
        return jsonify({"success": False, "error": "item_type and item_id required"}), 400
    from backend.services.user_engagement import remove_favorite
    return jsonify(remove_favorite(user_id, item_type, item_id)), 200


# ==================== SETTINGS ====================

@user_account_bp.route("/api/user/settings", methods=["GET"])
def user_settings_get():
    """Get user settings/preferences."""
    user_id = _resolve()
    from backend.services.user_engagement import get_settings
    return jsonify(get_settings(user_id)), 200


@user_account_bp.route("/api/user/settings", methods=["POST"])
def user_settings_update():
    """Update user settings."""
    user_id = _resolve()
    data = request.get_json() or {}
    from backend.services.user_engagement import update_settings
    return jsonify(update_settings(user_id, data)), 200


# ==================== GENERATION HISTORY ====================

@user_account_bp.route("/api/user/generation-history", methods=["GET"])
def user_generation_history():
    """Get video generation history for user."""
    user_id = _resolve()
    limit = min(100, int(request.args.get("limit", 20)))
    from backend.services.user_engagement import get_generation_history
    return jsonify({"success": True, "user_id": user_id, **get_generation_history(user_id, limit=limit)}), 200


# ==================== AI USER CONTROLLER ====================

@user_account_bp.route("/api/user/ai/onboard", methods=["POST"])
def ai_onboard():
    """Trigger full AI onboarding for the current user."""
    user_id = _resolve()
    data = request.get_json() or {}
    username = data.get("username", "")
    return jsonify(ai_user_controller.onboard_new_user(user_id, username)), 200


@user_account_bp.route("/api/user/ai/analyze", methods=["GET"])
def ai_analyze():
    """AI analyzes user activity and returns personalized recommendations."""
    user_id = _resolve()
    return jsonify(ai_user_controller.analyze_user_activity(user_id)), 200


@user_account_bp.route("/api/user/ai/nudge", methods=["GET"])
def ai_nudge():
    """Get a contextual engagement nudge for the user."""
    user_id = _resolve()
    return jsonify(ai_user_controller.generate_engagement_nudge(user_id)), 200


@user_account_bp.route("/api/user/ai/next-actions", methods=["GET"])
def ai_next_actions():
    """Get AI-suggested next actions for the user."""
    user_id = _resolve()
    count = min(10, int(request.args.get("count", 3)))
    return jsonify(ai_user_controller.suggest_next_actions(user_id, count=count)), 200


@user_account_bp.route("/api/user/ai/profile", methods=["GET"])
def ai_profile():
    """Get AI-generated behavioral profile of the user."""
    user_id = _resolve()
    return jsonify(ai_user_controller.profile_user(user_id)), 200


@user_account_bp.route("/api/user/ai/activity", methods=["POST"])
def ai_activity_hook():
    """
    Generic activity hook. Frontend or other routes call this to trigger
    AI-driven quest progress, achievement checks, and engagement updates.
    Body: {"activity_type": "video_generated"|"theory_studied"|..., "metadata": {}}
    """
    user_id = _resolve()
    data = request.get_json() or {}
    activity_type = data.get("activity_type", "")
    if not activity_type:
        return jsonify({"success": False, "error": "activity_type required"}), 400
    return jsonify(ai_user_controller.on_user_activity(user_id, activity_type, metadata=data.get("metadata"))), 200


# ==================== AI ACCOUNT BUILDER & CONTROL ====================

@user_account_bp.route("/api/user/ai/control-panel", methods=["GET"])
def ai_control_panel():
    """Master AI control panel — health, profile, state, strategy, and available actions."""
    user_id = _resolve()
    return jsonify(ai_user_controller.ai_control_panel(user_id)), 200


@user_account_bp.route("/api/user/ai/health", methods=["GET"])
def ai_health():
    """AI account health check — detects issues and lists repair actions."""
    user_id = _resolve()
    return jsonify(ai_user_controller.account_health_check(user_id)), 200


@user_account_bp.route("/api/user/ai/build", methods=["POST"])
def ai_build():
    """Full AI account build-up: provision, points, engagement, skills, strategy."""
    user_id = _resolve()
    data = request.get_json() or {}
    username = data.get("username", "")
    return jsonify(ai_user_controller.ai_build_account(user_id, username)), 200


@user_account_bp.route("/api/user/ai/repair", methods=["POST"])
def ai_repair():
    """AI auto-repairs all detected account gaps."""
    user_id = _resolve()
    return jsonify(ai_user_controller.auto_repair_account(user_id)), 200


@user_account_bp.route("/api/user/ai/boost", methods=["POST"])
def ai_boost():
    """Apply an AI-managed strategic boost. Body: {"boost_type": "balanced"|"xp"|"coins"|"battle"|"knowledge"|"social"}"""
    user_id = _resolve()
    data = request.get_json() or {}
    boost_type = data.get("boost_type", "balanced")
    return jsonify(ai_user_controller.ai_boost_account(user_id, boost_type)), 200


@user_account_bp.route("/api/user/ai/level-up", methods=["POST"])
def ai_level_up():
    """AI awards XP based on engagement and may trigger a level-up."""
    user_id = _resolve()
    return jsonify(ai_user_controller.ai_level_up(user_id)), 200


@user_account_bp.route("/api/user/ai/manage-skills", methods=["POST"])
def ai_manage_skills():
    """AI reviews and manages agent skill assignments for the user."""
    user_id = _resolve()
    return jsonify(ai_user_controller.ai_manage_skills(user_id)), 200


# ==================== USER LIFECYCLE & STATE SAVES ====================

@user_account_bp.route("/api/user/classify", methods=["GET"])
def user_classify():
    """Classify user lifecycle stage: new / returning / dormant / churned / active."""
    user_id = _resolve()
    from backend.services.ai_user_state_manager import classify_user
    return jsonify(classify_user(user_id)), 200


@user_account_bp.route("/api/user/save", methods=["POST"])
def user_save():
    """Save a full state snapshot of the user account."""
    user_id = _resolve()
    data = request.get_json() or {}
    label = data.get("label", "manual")
    from backend.services.ai_user_state_manager import save_user_snapshot
    return jsonify(save_user_snapshot(user_id, label)), 200


@user_account_bp.route("/api/user/save/load", methods=["GET"])
def user_save_load():
    """Load the latest saved snapshot for the user."""
    user_id = _resolve()
    from backend.services.ai_user_state_manager import load_user_snapshot
    return jsonify(load_user_snapshot(user_id)), 200


@user_account_bp.route("/api/user/save/history", methods=["GET"])
def user_save_history():
    """Get save history (compact entries) for the user."""
    user_id = _resolve()
    from backend.services.ai_user_state_manager import get_save_history
    return jsonify(get_save_history(user_id)), 200


@user_account_bp.route("/api/user/save/restore", methods=["POST"])
def user_save_restore():
    """Restore user account from the latest saved snapshot."""
    user_id = _resolve()
    from backend.services.ai_user_state_manager import restore_user_state
    return jsonify(restore_user_state(user_id)), 200


@user_account_bp.route("/api/user/welcome-back", methods=["GET"])
def user_welcome_back():
    """
    Smart welcome-back endpoint. AI detects user type and returns appropriate response:
    - New users: onboarding data + AI welcome
    - Returning users: streak update + nudge
    - Dormant users: re-engagement boost + welcome back message
    - Active users: today's status + next actions
    """
    user_id = _resolve()
    from backend.services.ai_user_state_manager import classify_user
    classification = classify_user(user_id)
    lifecycle = classification.get("classification", "new")

    result = {
        "success": True,
        "user_id": user_id,
        "lifecycle": lifecycle,
        "classification": classification,
    }

    if lifecycle == "new":
        result["action"] = "onboarding"
        result["onboarding"] = ai_user_controller.onboard_new_user(user_id)
    elif lifecycle == "dormant" or lifecycle == "churned":
        from backend.services.user_engagement import record_login, add_notification
        record_login(user_id)
        result["action"] = "re_engagement"
        result["boost"] = ai_user_controller.ai_boost_account(user_id, "balanced")
        result["nudge"] = ai_user_controller.generate_engagement_nudge(user_id)
        add_notification(
            user_id,
            title="Welcome Back!",
            message=f"Good to see you again after {classification.get('days_since_last_visit', '?')} days! We've applied a bonus boost to your account.",
            category="welcome_back",
        )
    elif lifecycle == "returning":
        from backend.services.user_engagement import record_login
        record_login(user_id)
        result["action"] = "welcome_return"
        result["nudge"] = ai_user_controller.generate_engagement_nudge(user_id)
        result["next_actions"] = ai_user_controller.suggest_next_actions(user_id, count=3)
    else:
        result["action"] = "active_status"
        result["next_actions"] = ai_user_controller.suggest_next_actions(user_id, count=3)

    # Always include current state
    result["state"] = ai_user_controller._gather_user_state(user_id)
    return jsonify(result), 200


# ==================== DATABASE USER MANAGEMENT ====================

@user_account_bp.route("/api/user/db/account", methods=["GET"])
def user_db_account():
    """Get the current user's database account record."""
    user_id = _resolve()
    from backend.services.user_db_service import get_user_account
    account = get_user_account(user_id)
    if not account:
        return jsonify({"success": False, "user_id": user_id, "error": "No DB account found"}), 404
    return jsonify({"success": True, "user_id": user_id, "account": account}), 200


@user_account_bp.route("/api/user/db/all", methods=["GET"])
def user_db_all():
    """List all registered users in the database."""
    limit = min(200, int(request.args.get("limit", 50)))
    offset = max(0, int(request.args.get("offset", 0)))
    from backend.services.user_db_service import get_all_users
    return jsonify({"success": True, **get_all_users(limit=limit, offset=offset)}), 200
