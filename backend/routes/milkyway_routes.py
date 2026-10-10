"""Milky Way Galaxy Research Station Routes"""
from flask import Blueprint, send_from_directory, Response
import os

milkyway_bp = Blueprint('milkyway', __name__)

@milkyway_bp.route('/milkyway/', methods=['GET'], strict_slashes=False)
@milkyway_bp.route('/milkyway', methods=['GET'], strict_slashes=False)
def milkyway_index():
    """Milky Way Galaxy Research Station page"""
    try:
        # Try known server paths first
        known_paths = [
            '/var/www/html/vidgenerator/vidgenerator/milkyway/index.html',  # Production server path
            os.path.join('/var/www/html/vidgenerator', 'vidgenerator', 'milkyway', 'index.html'),
            os.path.join('/var/www/html/vidgenerator', 'milkyway', 'index.html'),
        ]
        
        # Also try calculated path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        calculated_path = os.path.join(base_path, 'vidgenerator', 'milkyway', 'index.html')
        if calculated_path not in known_paths:
            known_paths.append(calculated_path)
        
        for index_file in known_paths:
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
        
        return "Milky Way Research Station page not found", 404
    except Exception as e:
        return f"Error loading Milky Way page: {str(e)}", 500

