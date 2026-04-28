"""
Communication Psychology Routes
API for 25 theories, progress, study unlock, and activity log. Integrated with points, profile, trophies, shop, starmap.
All endpoints resolve user_id via session > query/body > identification.
"""
from flask import Blueprint, jsonify, request

from backend.services.communication_psychology_service import (
    get_theories_list,
    get_user_progress,
    study_theory,
    award_points_for_activity,
)

comm_psych_bp = Blueprint("communication_psychology", __name__)


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')


def _get_activity_log(user_id: str, limit: int = 50):
    """Return recent activity from comm_psych_activity_log (DB)."""
    try:
        from backend.services.communication_psychology_service import _db_tables_exist
        if not _db_tables_exist():
            return {"success": True, "activities": []}
        from sqlalchemy import text
        from src.db.models import db
        from src.app import create_app
        app = create_app()
        with app.app_context():
            rows = db.session.execute(
                text("""
                    SELECT id, user_id, activity_type, theory_id, amount, source, metadata, created_at
                    FROM comm_psych_activity_log WHERE user_id = :uid ORDER BY created_at DESC LIMIT :lim
                """),
                {"uid": user_id or "default_user", "lim": limit},
            ).fetchall()
        activities = []
        for r in rows:
            activities.append({
                "id": r[0], "user_id": r[1], "activity_type": r[2], "theory_id": r[3],
                "amount": r[4], "source": r[5], "metadata": r[6], "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7]),
            })
        return {"success": True, "activities": activities}
    except Exception as e:
        return {"success": False, "error": str(e), "activities": []}


@comm_psych_bp.route("/api/communication-psychology/theories", methods=["GET"])
def list_theories():
    """List all 25 theories and categories (for starmap, shop, profile)."""
    return jsonify(get_theories_list()), 200


@comm_psych_bp.route("/api/communication-psychology/progress", methods=["GET"])
def user_progress():
    """Get current user's unlocked theories and communication_psychology_points (for profile)."""
    user_id = _resolve_uid()
    return jsonify(get_user_progress(user_id)), 200


@comm_psych_bp.route("/api/communication-psychology/study", methods=["POST"])
def study():
    """Unlock a theory for the user; awards communication_psychology_points and checks trophies."""
    data = request.get_json() or {}
    user_id = _resolve_uid()
    theory_id = (data.get("theory_id") or "").strip()
    if not theory_id:
        return jsonify({"success": False, "error": "theory_id required"}), 400
    result = study_theory(user_id, theory_id)
    if not result.get("success"):
        return jsonify(result), 400
    try:
        from backend.services.ai_user_controller import on_user_activity
        on_user_activity(user_id, "theory_studied", {"theory_id": theory_id})
    except Exception:
        pass
    return jsonify(result), 200


@comm_psych_bp.route("/api/communication-psychology/award", methods=["POST"])
def award():
    """Award communication_psychology_points from external activity (generator, shop, etc.)."""
    data = request.get_json() or {}
    user_id = _resolve_uid()
    amount = float(data.get("amount", 0) or 0)
    source_activity = data.get("source", "api_award")
    metadata = data.get("metadata") or {}
    result = award_points_for_activity(user_id, amount, source_activity, metadata)
    return jsonify(result), 200 if result.get("success") else 400


@comm_psych_bp.route("/api/communication-psychology/activity", methods=["GET"])
def activity_log():
    """Get recent communication psychology activity (study, award) from database."""
    user_id = _resolve_uid()
    limit = min(100, int(request.args.get("limit", 50) or 50))
    result = _get_activity_log(user_id, limit=limit)
    return jsonify(result), 200
