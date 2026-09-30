"""Game Hub API — overview, unified quests, story progress."""
from flask import Blueprint, jsonify, request

game_hub_bp = Blueprint("game_hub", __name__)


def _uid() -> str:
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        return (data.get("user_id") or request.args.get("user_id") or "").strip() or "default_user"
    return (request.args.get("user_id") or "").strip() or "default_user"


@game_hub_bp.route("/api/game-hub/overview", methods=["GET"])
def game_hub_overview():
    try:
        from backend.services.game_hub_service import get_overview
        return jsonify(get_overview(_uid())), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@game_hub_bp.route("/api/game-hub/quests", methods=["GET"])
def game_hub_quests():
    try:
        from backend.services.trophy_quest_service import get_unified_quests
        from backend.services.quest_system import get_user_quests, get_quest_statistics

        uid = _uid()
        hub = get_unified_quests(uid)
        progression = get_user_quests(uid)
        stats = get_quest_statistics(uid)

        return jsonify({
            **hub,
            "progression": progression.get("progression"),
            "progression_levels": progression.get("levels") or [],
            "chapters": progression.get("chapters") or [],
            "total_progression_levels": progression.get("total_levels"),
            "quest_level": stats.get("quest_level"),
            "progression_quests": progression.get("quests") or [],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@game_hub_bp.route("/api/game-hub/quests/claim", methods=["POST"])
def game_hub_quest_claim():
    try:
        data = request.get_json(silent=True) or {}
        uid = (data.get("user_id") or "").strip() or "default_user"
        quest_id = (data.get("quest_id") or "").strip()

        if quest_id.startswith("progression_"):
            from backend.services.quest_system import claim_level_reward
            try:
                level_num = int(quest_id.replace("progression_", ""))
            except ValueError:
                return jsonify({"success": False, "error": "invalid_quest_id"}), 200
            return jsonify(claim_level_reward(uid, level_num)), 200

        from backend.services.trophy_quest_service import claim_quest
        return jsonify(claim_quest(uid, quest_id)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@game_hub_bp.route("/api/game-hub/stories/read", methods=["POST"])
def game_hub_story_read():
    try:
        data = request.get_json(silent=True) or {}
        uid = (data.get("user_id") or "").strip() or "default_user"
        story_id = (data.get("story_id") or "").strip()
        from backend.services.game_hub_service import mark_story_read
        return jsonify(mark_story_read(uid, story_id)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
