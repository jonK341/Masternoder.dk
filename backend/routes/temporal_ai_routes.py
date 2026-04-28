"""
Temporal AI Routes — AI steady presence across all 9 time perspectives.

Endpoints:
  GET  /api/temporal-ai/perspectives              — list all 9 perspectives (metadata only)
  GET  /api/temporal-ai/insight/<perspective>     — AI insight for one perspective
  GET  /api/temporal-ai/all                       — AI insights for all 9 (or subset)
  POST /api/temporal-ai/refresh                   — bust cache + regenerate
"""
from flask import Blueprint, jsonify, request

from backend.services.temporal_ai_service import (
    get_insight,
    get_all_insights,
    get_perspectives_list,
    bust_cache,
    PERSPECTIVES,
)

temporal_ai_bp = Blueprint("temporal_ai", __name__)


def _resolve_user() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=False, from_query=True)
    except Exception:
        return request.args.get("user_id", "default_user")


# ---------------------------------------------------------------------------
# GET /api/temporal-ai/perspectives
# ---------------------------------------------------------------------------
@temporal_ai_bp.route("/api/temporal-ai/perspectives", methods=["GET"])
def list_perspectives():
    """
    List all 9 temporal perspectives with metadata.
    No DB queries, no AI calls — instant response.
    """
    return jsonify({
        "success": True,
        "count": len(PERSPECTIVES),
        "perspectives": get_perspectives_list(),
    }), 200


# ---------------------------------------------------------------------------
# GET /api/temporal-ai/insight/<perspective>
# ---------------------------------------------------------------------------
@temporal_ai_bp.route("/api/temporal-ai/insight/<perspective>", methods=["GET"])
def get_single_insight(perspective: str):
    """
    Get AI insight for one perspective.

    Query params:
      user_id      : filter data to a specific user (optional)
      force        : "true" to bypass cache
    """
    try:
        user_id = _resolve_user()
        force = request.args.get("force", "").lower() in ("true", "1", "yes")
        result = get_insight(perspective, user_id=user_id, force_refresh=force)
        status = 200 if result.get("success") else 200
        return jsonify(result), status
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


# ---------------------------------------------------------------------------
# GET /api/temporal-ai/all
# ---------------------------------------------------------------------------
@temporal_ai_bp.route("/api/temporal-ai/all", methods=["GET"])
def get_all():
    """
    Get AI insights for all 9 perspectives in one call.

    Query params:
      user_id      : filter to a specific user
      perspectives : comma-separated subset, e.g. "now,daily,monthly"
      force        : "true" to bypass all caches
    """
    try:
        user_id = _resolve_user()
        force = request.args.get("force", "").lower() in ("true", "1", "yes")
        subset_param = request.args.get("perspectives", "").strip()
        subset = [p.strip() for p in subset_param.split(",") if p.strip()] or None

        # Validate subset keys
        if subset:
            invalid = [p for p in subset if p not in PERSPECTIVES]
            if invalid:
                return jsonify({
                    "success": False,
                    "error": f"Unknown perspectives: {invalid}. "
                             f"Valid: {list(PERSPECTIVES.keys())}",
                }), 200

        result = get_all_insights(user_id=user_id, perspectives=subset, force_refresh=force)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200


# ---------------------------------------------------------------------------
# POST /api/temporal-ai/refresh
# ---------------------------------------------------------------------------
@temporal_ai_bp.route("/api/temporal-ai/refresh", methods=["POST"])
def refresh_insights():
    """
    Bust the insight cache and return fresh data.

    Body (JSON, all optional):
      user_id      : bust cache for specific user (omit for global bust)
      perspectives : list of specific perspectives to refresh
      fetch        : true (default) = also return fresh insights after bust
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_user()) or None
        perspectives = data.get("perspectives") or None
        fetch = data.get("fetch", True)

        cleared = bust_cache(user_id)

        if fetch:
            result = get_all_insights(
                user_id=user_id,
                perspectives=perspectives,
                force_refresh=True,
            )
            return jsonify({
                "success": True,
                "cache_cleared": cleared,
                **result,
            }), 200

        return jsonify({
            "success": True,
            "cache_cleared": cleared,
            "message": "Cache cleared. Call /api/temporal-ai/all to get fresh insights.",
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 200
