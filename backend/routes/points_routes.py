"""
Points Routes
Provides /api/points/all and /api/points/analytics.
All endpoints resolve user_id via session > query > identification.
"""
from flask import Blueprint, jsonify, request

from backend.services.unified_points_database import unified_points_db
from backend.services.account_resolution_service import resolve_user_id
from backend.middleware.response_cache_middleware import cached_response


points_bp = Blueprint("points", __name__)

def _default_points_payload():
    """Stable payload contract for all frontend counters."""
    return {
        "xp_total": 0,
        "level": 1,
        "generation_points": 0,
        "activity_points": 0,
        "battle_points": 0,
        "quest_points": 0,
        "game_points": 0,
        "social_points": 0,
        "knowledge_points": 0,
        "stats_points_total": 0,
        "stats_points_available": 0,
        "achievements_earned": 0,
        "milestones_reached": 0,
        "trophy_points": 0,
        "trophies_collected": 0,
        "coins": 0,
        "credits": 0,
        "mn2_balance": 0,
        "crypto_points": 0,
        "accuracy_grade": "A+",
        "systems": {},
    }


@points_bp.route("/api/points/all", methods=["GET"])
@cached_response(ttl=60)
def points_all():
    """Return all points used by the frontend counters. Returns 200 with empty points on failure so pages still load."""
    user_id = resolve_user_id(from_body=False, from_query=True)
    points = _default_points_payload()
    try:
        result = {"success": False}
        if unified_points_db:
            if hasattr(unified_points_db, "get_all_points"):
                result = unified_points_db.get_all_points(user_id)
            elif hasattr(unified_points_db, "get_user_points"):
                # Legacy compatibility path
                legacy = unified_points_db.get_user_points(user_id)
                result = {"success": True, "points": legacy if isinstance(legacy, dict) else {}}
            else:
                # Enhanced DB fallback if a different class is imported in production
                try:
                    from backend.services.unified_points_database_enhanced import unified_points_db_enhanced
                    if unified_points_db_enhanced and hasattr(unified_points_db_enhanced, "get_all_points"):
                        result = unified_points_db_enhanced.get_all_points(user_id)
                except Exception:
                    pass
    except Exception as e:
        result = {"success": False, "error": str(e)}
    if result.get("success"):
        payload = result.get("points", {}) if isinstance(result.get("points"), dict) else {}
        points.update(payload)
        return jsonify({"success": True, "user_id": user_id, "points": points}), 200
    # Return 200 with empty points so frontend counters/trophies page don't break; error in body for debugging
    return jsonify({
        "success": False,
        "user_id": user_id,
        "points": points,
        "error": result.get("error", "Unknown error")
    }), 200


@points_bp.route("/api/points/analytics", methods=["GET"])
def points_analytics():
    """Daily aggregates and summary when point_aggregates_daily / point_transactions exist."""
    try:
        user_id = resolve_user_id(from_body=False, from_query=True)
        days = min(90, max(1, int(request.args.get("days", 30))))
        from backend.services.points_db_service import (
            points_analytics_tables_exist,
            point_transactions_exist,
            get_analytics_daily,
            get_analytics_summary,
            refresh_daily_aggregates,
        )
        out = {"success": True, "user_id": user_id, "daily": [], "summary": None}
        if points_analytics_tables_exist():
            out["daily"] = get_analytics_daily(user_id, days=days) or []
            refresh_daily_aggregates(days=7)
        if point_transactions_exist():
            out["summary"] = get_analytics_summary(user_id, days=days)
        return jsonify(out), 200
    except Exception as e:
        # Keep dashboard/pages alive even if analytics tables/services are unavailable.
        return jsonify({
            "success": False,
            "error": str(e),
            "daily": [],
            "summary": None,
            "message": "Analytics unavailable; returned safe empty payload"
        }), 200


_POINTS_ADD_BLOCKED = frozenset({
    "mn2_balance",
    "coins",
    "casino_fiat_balance",
    "mn2_staked",
    "shop_balance",
})


@points_bp.route("/api/points/add", methods=["POST"])
def points_add():
    """Add non-cash points. Template services post user_id, point_type, amount, source."""
    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or request.args.get("user_id") or "").strip()
    point_type = (data.get("point_type") or data.get("type") or "").strip()
    source = (data.get("source") or "api").strip() or "api"
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    if not point_type:
        return jsonify({"success": False, "error": "point_type required"}), 400
    if point_type in _POINTS_ADD_BLOCKED:
        return jsonify({"success": False, "error": "point_type_not_allowed"}), 400
    try:
        amount = float(data.get("amount") or 0)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "amount must be a number"}), 400
    if amount == 0:
        return jsonify({"success": False, "error": "amount must be non-zero"}), 400
    try:
        result = unified_points_db.add_points(user_id, point_type, amount, source, {"via": "api/points/add"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    status = 200 if result.get("success") else 400
    return jsonify(result), status

