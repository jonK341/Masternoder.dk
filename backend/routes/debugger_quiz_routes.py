"""Debugger quiz reward. Anonymous sessions are rejected; a passing score credits MN2."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

debugger_quiz_bp = Blueprint("debugger_quiz", __name__)

_ANONYMOUS = {"", "default_user", "anonymous"}
_PASS_RATIO = 0.8
_MAX_MN2 = 0.01


@debugger_quiz_bp.route("/api/debugger/quiz/submit", methods=["POST"])
def submit_debugger_quiz():
    data = request.get_json(silent=True) or {}
    user_id = (data.get("user_id") or "").strip()
    if user_id in _ANONYMOUS:
        return jsonify({"success": False, "error": "sign_in_required"}), 403
    try:
        correct = int(data.get("correct"))
        total = int(data.get("total"))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "invalid_score"}), 400
    if total <= 0 or correct < 0 or correct > total:
        return jsonify({"success": False, "error": "invalid_score"}), 400

    ratio = correct / total
    amount = round(_MAX_MN2 * ratio, 6) if ratio >= _PASS_RATIO else 0.0
    day = (data.get("day") or datetime.now(timezone.utc).strftime("%Y-%m-%d")).strip()
    awarded = 0.0
    duplicate = False
    if amount > 0:
        from backend.services.unified_points_database import unified_points_db

        result = unified_points_db.add_points(
            user_id,
            "mn2_balance",
            amount,
            "debugger_quiz",
            {
                "reference": f"debugger-quiz:{user_id}:{day}",
                "correct": correct,
                "total": total,
            },
        )
        if not result.get("success"):
            return jsonify({"success": False, "error": result.get("error") or "award_failed", "mn2_awarded": 0.0}), 200
        duplicate = bool(result.get("duplicate"))
        awarded = 0.0 if duplicate else amount

    return jsonify({
        "success": True,
        "user_id": user_id,
        "correct": correct,
        "total": total,
        "day": day,
        "duplicate": duplicate,
        "mn2_awarded": awarded,
        "amount_mn2": awarded,
    }), 200
