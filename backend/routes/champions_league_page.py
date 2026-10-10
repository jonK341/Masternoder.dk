"""
Champions League Page Route - Serve champions league HTML page
"""
from flask import Blueprint, Response
import os

champions_league_page_bp = Blueprint('champions_league_page', __name__)


@champions_league_page_bp.route('/champions-league', methods=['GET'], strict_slashes=False)
@champions_league_page_bp.route('/champions-league/', methods=['GET'], strict_slashes=False)
@champions_league_page_bp.route('/champions-league/index.html', methods=['GET'], strict_slashes=False)
def champions_league_page():
    """Serve champions league page"""
    try:
        champions_file = '/var/www/html/vidgenerator/vidgenerator/champions-league/index.html'
        
        if os.path.exists(champions_file):
            with open(champions_file, 'r', encoding='utf-8') as f:
                content = f.read()
            response = Response(content, mimetype='text/html; charset=utf-8')
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
            return response
        else:
            return f"Error: Champions League page not found at {champions_file}", 404
    except Exception as e:
        return f"Error loading Champions League page: {str(e)}", 500

