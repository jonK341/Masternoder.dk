"""
Dashboard Page Routes
Routes for serving the dashboard HTML page and profile page
"""
from flask import Blueprint, redirect
import os

dashboard_page_bp = Blueprint('dashboard_page', __name__)
profile_page_bp = Blueprint('profile_page', __name__)
stats_page_bp = Blueprint('stats_page', __name__)
social_page_bp = Blueprint('social_page', __name__)
trophies_page_bp = Blueprint('trophies_page', __name__)
points_page_bp = Blueprint('points_page', __name__)
analytics_page_bp = Blueprint('analytics_page', __name__)

@dashboard_page_bp.route('/vidgenerator/dashboard', methods=['GET'])
@dashboard_page_bp.route('/vidgenerator/dashboard/', methods=['GET'])
@dashboard_page_bp.route('/vidgenerator/dashboard/index.html', methods=['GET'])
@dashboard_page_bp.route('/dashboard', methods=['GET'])
@dashboard_page_bp.route('/dashboard/', methods=['GET'])
@dashboard_page_bp.route('/dashboard/index.html', methods=['GET'])
def dashboard_index():
    """Legacy dashboard URL → unified profile (activity tab)."""
    return redirect('/profile?tab=activity', code=301)

@profile_page_bp.route('/vidgenerator/profile', methods=['GET'])
@profile_page_bp.route('/vidgenerator/profile/', methods=['GET'])
@profile_page_bp.route('/vidgenerator/profile/index.html', methods=['GET'])
@profile_page_bp.route('/profile', methods=['GET'])
@profile_page_bp.route('/profile/', methods=['GET'])
@profile_page_bp.route('/profile/index.html', methods=['GET'])
def profile_index():
    """Profile page - serves the HTML file"""
    try:
        # Get the base path (project root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        profile_path = os.path.join(base_path, 'profile', 'index.html')
        if not os.path.exists(profile_path):
            profile_path = os.path.join(base_path, 'vidgenerator', 'profile', 'index.html')
        
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        
        # Fallback HTML if file doesn't exist
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Profile - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <style>
        body {{ 
            padding: 100px 20px 60px; 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
            color: #ffffff;
        }}
        .error-container {{
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            padding: 40px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 20px;
            border: 2px solid rgba(255, 0, 0, 0.3);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Profile Page Not Found</h1>
        <p>The profile page file could not be located at: {profile_path}</p>
    </div>
</body>
</html>"""
        
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading profile page: {str(e)}", 500

@stats_page_bp.route('/vidgenerator/stats', methods=['GET'])
@stats_page_bp.route('/vidgenerator/stats/', methods=['GET'])
@stats_page_bp.route('/vidgenerator/stats/index.html', methods=['GET'])
@stats_page_bp.route('/stats', methods=['GET'])
@stats_page_bp.route('/stats/', methods=['GET'])
@stats_page_bp.route('/stats/index.html', methods=['GET'])
def stats_index():
    """Legacy stats URL → unified profile (points tab)."""
    return redirect('/profile?tab=points', code=301)

@social_page_bp.route('/vidgenerator/social', methods=['GET'])
@social_page_bp.route('/vidgenerator/social/', methods=['GET'])
@social_page_bp.route('/vidgenerator/social/index.html', methods=['GET'])
@social_page_bp.route('/social', methods=['GET'])
@social_page_bp.route('/social/', methods=['GET'])
@social_page_bp.route('/social/index.html', methods=['GET'])
def social_index():
    """Social page - serves the HTML file"""
    try:
        # Get the base path (project root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        social_path = os.path.join(base_path, 'vidgenerator', 'social', 'index.html')
        
        if os.path.exists(social_path):
            with open(social_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        # Fallback HTML if file doesn't exist
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Social - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <style>
        body {{ 
            padding: 100px 20px 60px; 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
            color: #ffffff;
        }}
        .error-container {{
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            padding: 40px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 20px;
            border: 2px solid rgba(255, 0, 0, 0.3);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Social Page Not Found</h1>
        <p>The social page file could not be located at: {social_path}</p>
    </div>
</body>
</html>"""
        
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading social page: {str(e)}", 500


@social_page_bp.route('/social-monitor', methods=['GET'])
@social_page_bp.route('/social-monitor/', methods=['GET'])
@social_page_bp.route('/social-monitor/index.html', methods=['GET'])
def social_monitor_index():
    """Social network monitor page."""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        monitor_path = os.path.join(base_path, 'social-monitor', 'index.html')
        if os.path.exists(monitor_path):
            with open(monitor_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {
                'Content-Type': 'text/html; charset=utf-8',
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        return "Social monitor page not found", 404
    except Exception as e:
        return f"Error loading social monitor page: {str(e)}", 500

@trophies_page_bp.route('/vidgenerator/trophies', methods=['GET'])
@trophies_page_bp.route('/vidgenerator/trophies/', methods=['GET'])
@trophies_page_bp.route('/vidgenerator/trophies/index.html', methods=['GET'])
@trophies_page_bp.route('/trophies', methods=['GET'])
@trophies_page_bp.route('/trophies/', methods=['GET'])
@trophies_page_bp.route('/trophies/index.html', methods=['GET'])
def trophies_index():
    """Trophies page - serves the HTML file"""
    try:
        # Get the base path (project root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        trophies_path = os.path.join(base_path, 'vidgenerator', 'trophies', 'index.html')
        
        if os.path.exists(trophies_path):
            with open(trophies_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return content, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
        # Fallback HTML if file doesn't exist
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Trophies - MasterNoder</title>
    <link rel="stylesheet" href="/vidgenerator/static/css/modern-design-system.css">
    <style>
        body {{ 
            padding: 100px 20px 60px; 
            font-family: Arial, sans-serif; 
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
            color: #ffffff;
        }}
        .error-container {{
            max-width: 800px;
            margin: 0 auto;
            text-align: center;
            padding: 40px;
            background: rgba(255, 0, 0, 0.1);
            border-radius: 20px;
            border: 2px solid rgba(255, 0, 0, 0.3);
        }}
    </style>
</head>
<body>
    <div class="error-container">
        <h1>Trophies Page Not Found</h1>
        <p>The trophies page file could not be located at: {trophies_path}</p>
    </div>
</body>
</html>"""
        
        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}
        
    except Exception as e:
        return f"Error loading trophies page: {str(e)}", 500

@points_page_bp.route('/vidgenerator/points', methods=['GET'])
@points_page_bp.route('/vidgenerator/points/', methods=['GET'])
@points_page_bp.route('/vidgenerator/points/index.html', methods=['GET'])
@points_page_bp.route('/points', methods=['GET'])
@points_page_bp.route('/points/', methods=['GET'])
@points_page_bp.route('/points/index.html', methods=['GET'])
def points_index():
    """Legacy points URL → unified profile (points tab)."""
    return redirect('/profile?tab=points', code=301)

@analytics_page_bp.route('/vidgenerator/analytics', methods=['GET'])
@analytics_page_bp.route('/vidgenerator/analytics/', methods=['GET'])
@analytics_page_bp.route('/vidgenerator/analytics/index.html', methods=['GET'])
@analytics_page_bp.route('/analytics', methods=['GET'])
@analytics_page_bp.route('/analytics/', methods=['GET'])
@analytics_page_bp.route('/analytics/index.html', methods=['GET'])
def analytics_index():
    """Legacy analytics URL → unified profile (activity tab)."""
    return redirect('/profile?tab=activity', code=301)
