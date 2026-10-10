"""
Victory Tech Tree routes
Serves the victory emblems and trophies tech tree interface
"""
from flask import Blueprint, Response
import os

victory_tech_tree_bp = Blueprint('victory_tech_tree', __name__)


# Note: Middleware strips /vidgenerator, so routes should be /tech-tree (not /vidgenerator/tech-tree)
@victory_tech_tree_bp.route('/victory-tech-tree', methods=['GET'], strict_slashes=False)
@victory_tech_tree_bp.route('/victory-tech-tree/', methods=['GET'], strict_slashes=False)
@victory_tech_tree_bp.route('/victory-tech-tree/index.html', methods=['GET'], strict_slashes=False)
@victory_tech_tree_bp.route('/tech-tree', methods=['GET'], strict_slashes=False)
@victory_tech_tree_bp.route('/tech-tree/', methods=['GET'], strict_slashes=False)
@victory_tech_tree_bp.route('/tech-tree/index.html', methods=['GET'], strict_slashes=False)
def victory_tech_tree_index():
    """Victory Tech Tree main page"""
    try:
        # Calculate base path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        victory_path = os.path.join(base_path, 'vidgenerator', 'victory-tech-tree')
        index_file = os.path.join(victory_path, 'index.html')
        
        # Try known server paths (both server and local)
        known_paths = [
            '/var/www/html/vidgenerator/vidgenerator/victory-tech-tree/index.html',
            '/var/www/html/vidgenerator/victory-tech-tree/index.html',
            os.path.join('/var/www/html/vidgenerator', 'vidgenerator', 'victory-tech-tree', 'index.html'),
            os.path.join(base_path, 'vidgenerator', 'victory-tech-tree', 'index.html'),
            os.path.join(base_path, 'vidgenerator', 'vidgenerator', 'victory-tech-tree', 'index.html'),
            index_file
        ]
        
        for path in known_paths:
            try:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    response = Response(content, mimetype='text/html; charset=utf-8')
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
            except Exception:
                continue
        
        # Fallback: Return a basic HTML page instead of 404
        fallback_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tech Tree - MasterNoder</title>
    <style>
        body { font-family: Arial, sans-serif; background: #000; color: #fff; padding: 40px; text-align: center; }
        a { color: #00ff88; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>Victory Tech Tree</h1>
    <p>Loading tech tree...</p>
    <p><a href="/vidgenerator/">← Back to Home</a></p>
    <script>
        // Try to load tech tree data
        fetch('/vidgenerator/api/tech-tree?user_id=default_user')
            .then(r => r.json())
            .then(data => console.log('Tech tree data:', data))
            .catch(e => console.error('Error loading tech tree:', e));
    </script>
</body>
</html>"""
        response = Response(fallback_html, mimetype='text/html; charset=utf-8')
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        return response
        
    except Exception as e:
        # Return fallback HTML even on error
        fallback_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tech Tree - MasterNoder</title>
    <style>
        body {{ font-family: Arial, sans-serif; background: #000; color: #fff; padding: 40px; text-align: center; }}
        a {{ color: #00ff88; }}
    </style>
</head>
<body>
    <h1>Victory Tech Tree</h1>
    <p>Error loading page: {str(e)}</p>
    <p><a href="/vidgenerator/">← Back to Home</a></p>
</body>
</html>"""
        return Response(fallback_html, mimetype='text/html; charset=utf-8'), 200

