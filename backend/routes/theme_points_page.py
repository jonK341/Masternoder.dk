"""
Theme Points Page Route - Serve theme-points HTML page
"""
from flask import Blueprint, Response, send_file
import os

theme_points_page_bp = Blueprint('theme_points_page', __name__)


@theme_points_page_bp.route('/theme-points', methods=['GET'], strict_slashes=False)
@theme_points_page_bp.route('/theme-points/', methods=['GET'], strict_slashes=False)
@theme_points_page_bp.route('/theme-points/index.html', methods=['GET'], strict_slashes=False)
def theme_points_page():
    """Serve theme-points page"""
    try:
        # Try multiple possible paths
        possible_paths = [
            '/var/www/html/vidgenerator/vidgenerator/theme-points/index.html',
            '/var/www/html/vidgenerator/theme-points/index.html',
        ]
        
        # Also try calculated path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calculated_paths = [
            os.path.join(base_path, 'vidgenerator', 'theme-points', 'index.html'),
            os.path.join(base_path, 'vidgenerator', 'vidgenerator', 'theme-points', 'index.html'),
        ]
        
        all_paths = possible_paths + calculated_paths
        
        for file_path in all_paths:
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='text/html; charset=utf-8')
        
        return f"Error: Theme points page not found. Tried: {', '.join(all_paths)}", 404
    except Exception as e:
        return f"Error loading theme points page: {str(e)}", 500

