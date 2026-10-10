"""
Video Editor Page Route - Serve video editor HTML page
"""
from flask import Blueprint, send_file
import os

video_editor_page_bp = Blueprint('video_editor_page', __name__)


@video_editor_page_bp.route('/vidgenerator/editor', methods=['GET'], strict_slashes=False)
@video_editor_page_bp.route('/vidgenerator/editor/', methods=['GET'], strict_slashes=False)
@video_editor_page_bp.route('/vidgenerator/editor/index.html', methods=['GET'], strict_slashes=False)
def video_editor_page():
    """Serve video editor page"""
    try:
        editor_file = '/var/www/html/vidgenerator/vidgenerator/editor/index.html'
        
        # Also try calculated path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calculated_path = os.path.join(base_path, 'vidgenerator', 'editor', 'index.html')
        
        for file_path in [editor_file, calculated_path]:
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='text/html; charset=utf-8')
        
        return f"Error: Video editor page not found. Tried: {editor_file}, {calculated_path}", 404
    except Exception as e:
        return f"Error loading video editor page: {str(e)}", 500

