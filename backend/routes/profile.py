"""
Profile page route - DEPRECATED: Profile route is now handled directly in app.py
This blueprint is kept for backwards compatibility but routes are disabled
"""
from flask import Blueprint, Response
import os

profile_page_bp = Blueprint('profile_page', __name__)

# Profile routes removed - handled by direct route in app.py to avoid conflicts
# @profile_page_bp.route('/profile')
# @profile_page_bp.route('/profile/')
def profile_index():
    """Profile page"""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        profile_path = os.path.join(base_path, 'vidgenerator', 'profile')
        index_file = os.path.join(profile_path, 'index.html')
        
        print(f"[Profile] Looking for profile page at: {index_file}", flush=True)
        print(f"[Profile] Base path: {base_path}", flush=True)
        print(f"[Profile] File exists: {os.path.exists(index_file)}", flush=True)
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[Profile] Serving profile page ({len(content)} bytes)", flush=True)
            return Response(content, mimetype='text/html; charset=utf-8')
        else:
            # Try alternative paths
            alt_paths = [
                os.path.join(base_path, 'vidgenerator', 'profile', 'index.html'),
                '/var/www/html/vidgenerator/vidgenerator/profile/index.html',
                os.path.join(os.getcwd(), 'vidgenerator', 'profile', 'index.html'),
            ]
            for alt_path in alt_paths:
                if os.path.exists(alt_path):
                    print(f"[Profile] Found at alternative path: {alt_path}", flush=True)
                    with open(alt_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    return Response(content, mimetype='text/html; charset=utf-8')
            
            error_msg = f"Profile page not found. Tried: {index_file}"
            print(f"[Profile] {error_msg}", flush=True)
            return error_msg, 404
    except Exception as e:
        import traceback
        error_msg = f"Error serving profile page: {str(e)}\n{traceback.format_exc()}"
        print(f"[Profile] {error_msg}", flush=True)
        return f"Error serving profile page: {str(e)}", 500
