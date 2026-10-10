"""
Quest Page Route
"""
from flask import Blueprint, jsonify, request, send_from_directory
import os

quest_page_bp = Blueprint('quest_page', __name__)

@quest_page_bp.route('/quests')
@quest_page_bp.route('/quests/')
@quest_page_bp.route('/quests/index.html')
def quest_page():
    """Serve quest page"""
    quests_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vidgenerator', 'quests')
    return send_from_directory(quests_dir, 'index.html')


@quest_page_bp.route("/api/quests/user/<user_id>", methods=["GET"])
def quests_for_user(user_id):
    """Progression board for /quests/."""
    try:
        from backend.services.quest_system import get_user_quests
        chapter = request.args.get("chapter", type=int)
        return jsonify(get_user_quests(user_id, chapter=chapter)), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

