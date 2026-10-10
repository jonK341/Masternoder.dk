"""
Quest Page Route
"""
from flask import Blueprint, send_from_directory
import os

quest_page_bp = Blueprint('quest_page', __name__)

@quest_page_bp.route('/quests')
@quest_page_bp.route('/quests/')
@quest_page_bp.route('/quests/index.html')
def quest_page():
    """Serve quest page"""
    quests_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vidgenerator', 'quests')
    return send_from_directory(quests_dir, 'index.html')

