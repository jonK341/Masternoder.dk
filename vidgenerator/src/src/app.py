"""Flask application factory for Documentary Generator"""
import os
from flask import Flask, request, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from src.db.models import db
# Import routes - from routes package (routes/__init__.py)
try:
    # Try importing from routes package (routes/__init__.py)
    from src.web.routes import register_routes
except ImportError:
    # Fallback - routes package not available, use routes.py
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web'))
    from routes import register_routes as register_routes_from_file
    register_routes = register_routes_from_file

# Import API blueprint - handle import errors gracefully
try:
    from src.api import api_bp
except ImportError as e:
    print(f"WARNING: Could not import api_bp: {e}")
    # Create a dummy blueprint if import fails
    from flask import Blueprint
    api_bp = Blueprint('api', __name__, url_prefix='/api')

class ApplicationRootMiddleware:
    """Simplified WSGI middleware to strip /vidgenerator from PATH_INFO"""
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        # Simple: if PATH_INFO starts with /vidgenerator, strip it
        # Apache proxy forwards /vidgenerator/* to Flask as /vidgenerator/*
        # We strip /vidgenerator so routes without prefix can match
        
        path_info = environ.get('PATH_INFO', '') or '/'
        original_path = path_info
        
        # If path starts with /vidgenerator, strip it
        if path_info.startswith('/vidgenerator'):
            new_path = path_info[len('/vidgenerator'):] or '/'
            # Ensure path starts with /
            if not new_path.startswith('/'):
                new_path = '/' + new_path
            environ['PATH_INFO'] = new_path
            environ['SCRIPT_NAME'] = '/vidgenerator'
            app_root = '/vidgenerator'
        else:
            app_root = ''
        
        # Store application root
        environ['_APPLICATION_ROOT'] = app_root
        
        # Debug logging - always log for API requests
        import sys
        req_method = environ.get('REQUEST_METHOD', '')
        new_path_info = environ.get('PATH_INFO', '')
        if req_method and ('api' in new_path_info or req_method in ['POST', 'GET', 'OPTIONS']):
            print(f"[WSGI] {req_method} {original_path} -> PATH_INFO: {new_path_info}, SCRIPT_NAME: {environ.get('SCRIPT_NAME')}", file=sys.stderr, flush=True)
        
        return self.app(environ, start_response)

def create_app():
    """Create and configure Flask application"""
    # Get the base path for templates and static files
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Try vidgenerator templates/static first (server files), then backend, then src/web
    vidgenerator_template_path = os.path.join(base_path, 'vidgenerator')
    vidgenerator_static_path = os.path.join(base_path, 'vidgenerator', 'static')
    backend_template_path = os.path.join(base_path, 'backend', 'templates')
    backend_static_path = os.path.join(base_path, 'backend', 'static')
    template_path = os.path.join(base_path, 'src', 'web', 'templates')
    static_path = os.path.join(base_path, 'src', 'web', 'static')
    
    # Priority: vidgenerator > backend > src/web
    if os.path.exists(vidgenerator_template_path):
        template_path = vidgenerator_template_path
        print(f"[App] Using vidgenerator templates: {template_path}")
    elif os.path.exists(backend_template_path):
        template_path = backend_template_path
        print(f"[App] Using backend templates: {template_path}")
    
    if os.path.exists(vidgenerator_static_path):
        static_path = vidgenerator_static_path
        print(f"[App] Using vidgenerator static: {static_path}")
    elif os.path.exists(backend_static_path):
        static_path = backend_static_path
        print(f"[App] Using backend static: {static_path}")
    
    # Dynamic application root based on request
    # For masternoder.dk (main domain) -> no prefix (root)
    # For vidgenerator.masternoder.dk or /vidgenerator path -> /vidgenerator prefix
    application_root_env = os.getenv('APPLICATION_ROOT', '').strip()
    
    # Function to determine application root dynamically based on request
    def get_application_root():
        """Determine application root based on environment or request context"""
        # If explicitly set in environment, use it
        if application_root_env and application_root_env != '/':
            root = application_root_env.rstrip('/')
            if not root.startswith('/'):
                root = '/' + root
            return root
        
        # For vidgenerator.masternoder.dk or /vidgenerator path -> /vidgenerator prefix
        return '/vidgenerator'  # Default for vidgenerator subdomain/path
    
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=template_path,
        static_folder=static_path,
        static_url_path='/static'
    )
    
    # Configure Flask
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///' + os.path.join(base_path, 'documentary_generator.db')
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # DISABLE ALL CACHING
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # No cache for static files
    app.config['TEMPLATES_AUTO_RELOAD'] = True  # Reload templates on every request
    app.jinja_env.auto_reload = True  # Force template reload
    app.jinja_env.cache_size = 0  # Disable Jinja2 template cache
    
    # DON'T set APPLICATION_ROOT in config - it requires SCRIPT_NAME matching
    # We handle application root manually via middleware and url_for override
    # Setting static_url_path can cause issues with nginx, so we'll keep it as /static
    # Since nginx rewrites URLs, Flask sees root paths but needs to generate /vidgenerator URLs
    
    # Initialize database
    db.init_app(app)
    
    # Standard solution: Use ProxyFix with x_prefix=1 (standard best practice)
    # This handles all reverse proxy headers correctly
    # NO custom middleware - let Flask handle routes naturally
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)
    
    # Add no-cache headers to all responses to prevent browser caching issues
    @app.after_request
    def add_no_cache_headers(response):
        """Add aggressive no-cache headers to prevent browser caching issues"""
        # Aggressive cache prevention
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        response.headers['X-Accel-Expires'] = '0'  # Nginx cache control
        response.headers.pop('ETag', None)  # Remove ETag to force revalidation
        response.headers.pop('Last-Modified', None)  # Remove Last-Modified
        
        # Add version/timestamp to force reload - use milliseconds for better uniqueness
        import time
        timestamp = int(time.time() * 1000)  # Milliseconds
        response.headers['X-Content-Version'] = str(timestamp)
        
        return response
    
    # Add global template variable for cache-busting
    @app.template_global()
    def cache_bust():
        """Generate a unique cache-busting parameter"""
        import time
        import random
        # Use both timestamp and random to ensure uniqueness
        return f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
    
    # Add version to all template contexts
    @app.context_processor
    def inject_version():
        """Inject version and cache-busting into all templates"""
        import time
        import random
        version = f"{int(time.time() * 1000)}_{random.randint(1000, 9999)}"
        return dict(
            cache_bust=lambda: version,  # Same version for entire request
            page_version=version
        )
    
    # Custom url_for that adds application_root prefix
    from flask import url_for as flask_url_for
    original_url_for = flask_url_for
    
    @app.template_global()
    def url_for(endpoint, **values):
        """Custom url_for that adds /vidgenerator prefix when needed"""
        # Get the original url_for result
        url = original_url_for(endpoint, **values)
        
        # If this is a vidgenerator request, ensure URL has /vidgenerator prefix
        # Check request context
        try:
            if request:
                host = request.host.lower()
                path = request.path
                # Check if this is vidgenerator request
                if 'vidgenerator' in host or path.startswith('/vidgenerator'):
                    current_root = '/vidgenerator'
                    # If URL doesn't start with /vidgenerator, add it
                    if not url.startswith('/vidgenerator') and not url.startswith('http'):
                        url = current_root + url
        except RuntimeError:
            # No request context - use default
            pass
        
        return url
    
    # Test url_for override
    with app.test_request_context('/vidgenerator/'):
        test_url = url_for('static', filename='css/style.css')
        expected = '/vidgenerator/static/css/style.css'
        if test_url == expected:
            print("[OK] url_for override test passed: " + test_url, flush=True)
        else:
            print(f"[DEBUG] Template url_for test: {test_url}", flush=True)
    
    # Register API blueprint
    try:
        app.register_blueprint(api_bp)
        print("[OK] API blueprint registered")
    except Exception as e:
        print(f"WARNING: Failed to register API blueprint: {e}")
        import traceback
        traceback.print_exc()
    
    # Register Micro integration blueprints FIRST (before other routes)
    # This ensures backend blueprints are registered before any potential conflicts
    try:
        from backend.register_blueprints import register_all_blueprints
        print("[App] Calling register_all_blueprints...", flush=True)
        register_all_blueprints(app)
        print("[App] Backend blueprints registration completed", flush=True)
    except ImportError as e:
        print(f"WARNING: Could not register Micro blueprints: {e}", flush=True)
        print("  This is OK if backend integration is not needed yet", flush=True)
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"WARNING: Error registering Micro blueprints: {e}", flush=True)
        import traceback
        traceback.print_exc()
    
    # Register routes (after backend blueprints to avoid conflicts)
    try:
        register_routes(app)
    except Exception as e:
        print(f"ERROR: Failed to register routes: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # NOTE: Cache headers are already handled by add_no_cache_headers() above
    # This duplicate handler was removed to prevent conflicts
    
    # Determine application root dynamically
    application_root = get_application_root()
    
    # DON'T set APPLICATION_ROOT in config - it requires SCRIPT_NAME matching which nginx rewrite doesn't provide
    # We handle it manually via middleware and url_for override
    print(f"Configured APPLICATION_ROOT: {application_root} (handled manually, nginx rewrites URLs, bypassed Werkzeug check)", flush=True)
    
    return app
