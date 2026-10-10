"""
Missing Page Routes - Create route handlers for pages without routes
Ensures all navigation links work
"""
from flask import Blueprint, Response, send_file
import os

# Create blueprints for missing pages
social_page_bp = Blueprint('social_page', __name__)
shop_page_bp = Blueprint('shop_page', __name__)
battle_page_bp = Blueprint('battle_page', __name__)

def serve_html_page(route_path, page_name):
    """Generic function to serve HTML pages"""
    @route_path.route(f'/{page_name}', methods=['GET'], strict_slashes=False)
    @route_path.route(f'/{page_name}/', methods=['GET'], strict_slashes=False)
    @route_path.route(f'/{page_name}/index.html', methods=['GET'], strict_slashes=False)
    def page_handler():
        """Serve HTML page"""
        try:
            # Try multiple possible paths
            possible_paths = [
                f'/var/www/html/vidgenerator/vidgenerator/{page_name}/index.html',
                f'/var/www/html/vidgenerator/{page_name}/index.html',
            ]
            
            # Also try calculated path
            base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            calculated_paths = [
                os.path.join(base_path, 'vidgenerator', page_name, 'index.html'),
                os.path.join(base_path, 'vidgenerator', 'vidgenerator', page_name, 'index.html'),
            ]
            
            all_paths = possible_paths + calculated_paths
            
            for file_path in all_paths:
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    response = Response(content, mimetype='text/html; charset=utf-8')
                    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
                    return response
            
            # Fallback HTML
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{page_name.title()} - MasterNoder</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body>
                <h1>{page_name.title()} Page</h1>
                <p>Page is loading...</p>
                <p><a href="/vidgenerator/">Back to Home</a></p>
            </body>
            </html>
            """, 200
        except Exception as e:
            return f"Error loading {page_name} page: {str(e)}", 500

# Social page routes
serve_html_page(social_page_bp, 'social')

# Shop page routes
serve_html_page(shop_page_bp, 'shop')

# Battle page routes (HTML page, separate from API)
@battle_page_bp.route('/battle', methods=['GET'], strict_slashes=False)
@battle_page_bp.route('/battle/', methods=['GET'], strict_slashes=False)
@battle_page_bp.route('/battle/index.html', methods=['GET'], strict_slashes=False)
def battle_page():
    """Serve battle HTML page"""
    try:
        possible_paths = [
            '/var/www/html/vidgenerator/vidgenerator/battle/index.html',
            '/var/www/html/vidgenerator/battle/index.html',
        ]
        
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calculated_paths = [
            os.path.join(base_path, 'vidgenerator', 'battle', 'index.html'),
            os.path.join(base_path, 'vidgenerator', 'vidgenerator', 'battle', 'index.html'),
        ]
        
        all_paths = possible_paths + calculated_paths
        
        for file_path in all_paths:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                response = Response(content, mimetype='text/html; charset=utf-8')
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
                return response
        
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Battle - MasterNoder</title>
            <meta charset="UTF-8">
        </head>
        <body>
            <h1>Battle Page</h1>
            <p>Battle system loading...</p>
            <p><a href="/vidgenerator/">Back to Home</a></p>
        </body>
        </html>
        """, 200
    except Exception as e:
        return f"Error loading battle page: {str(e)}", 500

