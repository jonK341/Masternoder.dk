"""
Danish Giga Divine Tech Tree routes
Serves the Danish-themed unified stats tech tree interface
"""
from flask import Blueprint, Response
import os

danish_divine_tech_tree_bp = Blueprint('danish_divine_tech_tree', __name__)


@danish_divine_tech_tree_bp.route('/danish-divine-tech-tree')
@danish_divine_tech_tree_bp.route('/danish-divine-tech-tree/')
def dansk_divine_tech_tree_index():
    """Danish Giga Divine Tech Tree main page"""
    try:
        # Calculate base path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        dansk_path = os.path.join(base_path, 'vidgenerator', 'danish-divine-tech-tree')
        index_file = os.path.join(dansk_path, 'index.html')
        
        # Try known server paths
        known_paths = [
            '/var/www/html/vidgenerator/vidgenerator/danish-divine-tech-tree/index.html',
            os.path.join('/var/www/html/vidgenerator', 'vidgenerator', 'danish-divine-tech-tree', 'index.html'),
            index_file
        ]
        
        for path in known_paths:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
                return response
        
        # Fallback: Return error message
        return f"Danish Divine Tech Tree page not found. Checked paths: {known_paths}", 404
        
    except Exception as e:
        return f"Error loading Danish Divine Tech Tree page: {str(e)}", 500

