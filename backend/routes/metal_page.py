"""
Metal Page Route - Serve metal HTML page
"""
from flask import Blueprint, Response, send_file
import os

metal_page_bp = Blueprint('metal_page', __name__)


@metal_page_bp.route('/metal', methods=['GET'], strict_slashes=False)
@metal_page_bp.route('/metal/', methods=['GET'], strict_slashes=False)
@metal_page_bp.route('/metal/index.html', methods=['GET'], strict_slashes=False)
def metal_page():
    """Serve metal page"""
    try:
        # Try multiple possible paths
        possible_paths = [
            '/var/www/html/vidgenerator/vidgenerator/metal/index.html',
            '/var/www/html/vidgenerator/metal/index.html',
        ]
        
        # Also try calculated path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calculated_paths = [
            os.path.join(base_path, 'vidgenerator', 'metal', 'index.html'),
            os.path.join(base_path, 'vidgenerator', 'vidgenerator', 'metal', 'index.html'),
        ]
        
        all_paths = possible_paths + calculated_paths
        
        for file_path in all_paths:
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='text/html; charset=utf-8')
        
        return f"Error: Metal page not found. Tried: {', '.join(all_paths)}", 404
    except Exception as e:
        return f"Error loading metal page: {str(e)}", 500

