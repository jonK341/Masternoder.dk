"""Progression quest page API — 90 levels across 9 entertainment chapters."""
from flask import Blueprint, jsonify, request

quest_page_bp = Blueprint("quest_page", __name__)


@quest_page_bp.route("/api/quests/user/<user_id>", methods=["GET"])
def quests_for_user(user_id):
    """Legacy + primary progression board endpoint for /quests/."""
    try:
        from backend.services.quest_system import get_user_quests
        chapter = request.args.get("chapter", type=int)
        return jsonify(get_user_quests(user_id, chapter=chapter)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quest_page_bp.route("/api/quests/progression/levels", methods=["GET"])
def progression_levels():
    try:
        from backend.services.quest_system import get_all_levels, get_chapters, TOTAL_LEVELS
        return jsonify({
            "success": True,
            "total_levels": TOTAL_LEVELS,
            "chapters": get_chapters(),
            "levels": get_all_levels(),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quest_page_bp.route("/api/quests/progression/claim", methods=["POST"])
def progression_claim():
    try:
        data = request.get_json(silent=True) or {}
        uid = (data.get("user_id") or "").strip()
        level = data.get("level")
        if not uid:
            return jsonify({"success": False, "error": "user_id required"}), 200
        if level is None:
            return jsonify({"success": False, "error": "level required"}), 200
        from backend.services.quest_system import claim_level_reward
        return jsonify(claim_level_reward(uid, int(level))), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quest_page_bp.route("/api/quests/progression/progress", methods=["POST"])
def progression_progress():
    try:
        data = request.get_json(silent=True) or {}
        uid = (data.get("user_id") or "").strip()
        action = (data.get("action") or "").strip()
        if not uid or not action:
            return jsonify({"success": False, "error": "user_id and action required"}), 200
        from backend.services.quest_system import update_quest_progress
        return jsonify(update_quest_progress(
            uid, action, increment=int(data.get("increment") or 1), **(data.get("meta") or {}),
        )), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
