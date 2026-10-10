"""Academic Perspective Page Route"""
from flask import Blueprint, send_from_directory, Response
import os

academic_perspective_page_bp = Blueprint('academic_perspective_page', __name__)

@academic_perspective_page_bp.route('/academic-perspective/', methods=['GET'], strict_slashes=False)
@academic_perspective_page_bp.route('/academic-perspective', methods=['GET'], strict_slashes=False)
def academic_perspective_index():
    """Academic Perspective page"""
    try:
        known_paths = [
            '/var/www/html/vidgenerator/vidgenerator/academic-perspective/index.html',
            os.path.join('/var/www/html/vidgenerator', 'vidgenerator', 'academic-perspective', 'index.html'),
            os.path.join('/var/www/html/vidgenerator', 'academic-perspective', 'index.html'),
        ]
        
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        calculated_path = os.path.join(base_path, 'vidgenerator', 'academic-perspective', 'index.html')
        if calculated_path not in known_paths:
            known_paths.append(calculated_path)
        
        for index_file in known_paths:
            if os.path.exists(index_file):
                with open(index_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                return response
        
        return "Academic Perspective page not found", 404
    except Exception as e:
        return f"Error loading Academic Perspective page: {str(e)}", 500

