"""
All Vidgenerator Pages Routes
Complete route coverage for all pages in vidgenerator subfolders
"""
from flask import Blueprint, Response
import os

all_vidgenerator_pages_bp = Blueprint('all_vidgenerator_pages', __name__)

def _serve_vidgenerator_page(page_name: str, page_title: str):
    """Serve any vidgenerator page"""
    try:
        # Get base path (project root)
        # __file__ is backend/routes/all_vidgenerator_pages_routes.py
        # Go up 2 levels to get project root
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Try multiple possible paths
        possible_paths = [
            # Local development path (most common)
            os.path.join(base_path, 'vidgenerator', page_name, 'index.html'),
            # Server path (if deployed)
            f'/var/www/html/vidgenerator/vidgenerator/{page_name}/index.html',
            f'/var/www/html/vidgenerator/{page_name}/index.html',
            # Alternative local path
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'vidgenerator', page_name, 'index.html'),
        ]
        
        # Debug: print paths being checked
        import sys
        print(f"[Trophies Route] Looking for page: {page_name}", file=sys.stderr, flush=True)
        print(f"[Trophies Route] Base path: {base_path}", file=sys.stderr, flush=True)
        
        for file_path in possible_paths:
            print(f"[Trophies Route] Checking: {file_path}", file=sys.stderr, flush=True)
            if os.path.exists(file_path):
                print(f"[Trophies Route] Found file at: {file_path}", file=sys.stderr, flush=True)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                return response
            else:
                print(f"[Trophies Route] File not found: {file_path}", file=sys.stderr, flush=True)
        
        # Fallback HTML
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{page_title} - MasterNoder</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; background: #000; color: #fff; padding: 40px; text-align: center; }}
                a {{ color: #00ff88; text-decoration: none; }}
            </style>
        </head>
        <body>
            <h1>{page_title}</h1>
            <p>Page loading...</p>
            <p><a href="/vidgenerator/">Back to Home</a></p>
        </body>
        </html>
        """, 200
    except Exception as e:
        return f"Error loading {page_name} page: {str(e)}", 500

# All vidgenerator pages
PAGES = [
    ('battlegrounds', 'Battlegrounds'),
    ('champions-league', 'Champions League'),
    ('victory-tech-tree', 'Victory Tech Tree'),
    ('danish-divine-tech-tree', 'Danish Divine Tech Tree'),
    ('academic-perspective', 'Academic Perspective'),
    ('milkyway', 'Milkyway'),
    ('editor', 'Editor'),
    ('monetization', 'Monetization'),
    ('beta_testing', 'Beta Testing'),
    ('advanced_calculator', 'Advanced Calculator'),
    ('theme_premium', 'Theme Premium'),
    ('leaderboards', 'Leaderboards'),
    ('time-achievement-guides', 'Time Achievement Guides'),
    ('trophies', 'Trophies'),
]

# Generate routes for all pages
for page_name, page_title in PAGES:
    route_name = page_name.replace('-', '_').replace('_', '_')
    
    @all_vidgenerator_pages_bp.route(f'/{page_name}', methods=['GET'], strict_slashes=False)
    @all_vidgenerator_pages_bp.route(f'/{page_name}/', methods=['GET'], strict_slashes=False)
    @all_vidgenerator_pages_bp.route(f'/{page_name}/index.html', methods=['GET'], strict_slashes=False)
    def page_handler(page_name=page_name, page_title=page_title):
        """Serve page"""
        return _serve_vidgenerator_page(page_name, page_title)
    
    # Set function name
    page_handler.__name__ = f'{route_name}_page'

