"""
Dashboard Page Route - Serve dashboard HTML page
"""
from flask import Blueprint, Response, send_file
import os

dashboard_page_bp = Blueprint('dashboard_page', __name__)


@dashboard_page_bp.route('/dashboard', methods=['GET'], strict_slashes=False)
@dashboard_page_bp.route('/dashboard/', methods=['GET'], strict_slashes=False)
@dashboard_page_bp.route('/dashboard/index.html', methods=['GET'], strict_slashes=False)
def dashboard_page():
    """Serve dashboard page"""
    try:
        dashboard_file = '/var/www/html/vidgenerator/vidgenerator/dashboard/index.html'
        
        # Also try calculated path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calculated_path = os.path.join(base_path, 'vidgenerator', 'dashboard', 'index.html')
        
        for file_path in [dashboard_file, calculated_path]:
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='text/html; charset=utf-8')
        
        return f"Error: Dashboard page not found. Tried: {dashboard_file}, {calculated_path}", 404
    except Exception as e:
        return f"Error loading dashboard page: {str(e)}", 500
