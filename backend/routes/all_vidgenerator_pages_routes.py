"""
Legacy page fallback routes — serve root index.html copies (vidgenerator/ tree removed).
"""
from flask import Blueprint, Response
import os

all_vidgenerator_pages_bp = Blueprint('all_vidgenerator_pages', __name__)

def _serve_vidgenerator_page(page_name: str, page_title: str):
    """Serve a public page from the project root (canonical site paths)."""
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        possible_paths = [
            os.path.join(base_path, page_name, 'index.html'),
        ]
        for file_path in possible_paths:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                return response
        
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
            <p><a href="/">Back to Home</a></p>
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

