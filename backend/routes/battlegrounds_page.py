"""
BattleGrounds Page Route - Serve battlegrounds HTML page
"""
from flask import Blueprint, Response
import os

battlegrounds_page_bp = Blueprint('battlegrounds_page', __name__)


@battlegrounds_page_bp.route('/battlegrounds', methods=['GET'], strict_slashes=False)
@battlegrounds_page_bp.route('/battlegrounds/', methods=['GET'], strict_slashes=False)
@battlegrounds_page_bp.route('/battlegrounds/index.html', methods=['GET'], strict_slashes=False)
def battlegrounds_page():
    """Serve battlegrounds page"""
    try:
        battlegrounds_file = '/var/www/html/vidgenerator/vidgenerator/battlegrounds/index.html'
        
        if os.path.exists(battlegrounds_file):
            with open(battlegrounds_file, 'r', encoding='utf-8') as f:
                content = f.read()
            response = Response(content, mimetype='text/html; charset=utf-8')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            return response
        else:
            return f"Error: BattleGrounds page not found at {battlegrounds_file}", 404
    except Exception as e:
        return f"Error loading BattleGrounds page: {str(e)}", 500

