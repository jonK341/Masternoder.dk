"""
Flask Application Factory
Creates and configures the Flask application instance
"""
import os
import sys
import threading
from flask import Flask

# Load .env from vidgenerator or project root (for DATABASE_URL etc.)
try:
    from dotenv import load_dotenv
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for env_path in [
        os.path.join(_project_root, "vidgenerator", ".env"),
        os.path.join(_project_root, ".env"),
    ]:
        if os.path.isfile(env_path):
            load_dotenv(env_path)
            break
except ImportError:
    pass

# Ensure project root is on sys.path so backend.* imports work (e.g. on server / uwsgi / python-proxy)
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root and _project_root not in sys.path:
    sys.path.insert(0, _project_root)
# Also set PYTHONPATH for child processes (e.g. uwsgi workers)
if _project_root:
    os.environ["PYTHONPATH"] = _project_root + os.pathsep + os.environ.get("PYTHONPATH", "")

# Import db from models to avoid circular imports
from src.db.models import db

_daemon_cached_app = None
_daemon_init_lock = threading.Lock()
_daemon_boot_logged = False


def _daemon_quiet() -> bool:
    return os.environ.get("DAEMON_QUIET", "").strip().lower() in ("1", "true", "yes", "on")


def _register_critical_blueprints(app):
    """Register critical blueprints (pages first, then gallery, missing_endpoints) when full registration fails."""
    try:
        from backend.routes.all_page_routes import all_page_bp
        app.register_blueprint(all_page_bp)
        print("  [OK] Registered all_page (fallback)")
    except Exception as e:
        print(f"  [WARN] Fallback all_page: {e}")
    try:
        from backend.routes.missing_endpoints_routes import missing_endpoints_bp
        app.register_blueprint(missing_endpoints_bp)
        print("  [OK] Registered missing_endpoints (fallback)")
    except Exception as e:
        print(f"  [WARN] Fallback missing_endpoints: {e}")
    try:
        from backend.routes.gallery_routes import gallery_bp
        app.register_blueprint(gallery_bp)
        print("  [OK] Registered gallery (fallback)")
    except Exception as e:
        print(f"  [WARN] Fallback gallery: {e}")


def create_app(config_name=None):
    """
    Application factory function
    Creates and configures a Flask application instance

    Args:
        config_name: Optional configuration name (defaults to environment-based)

    Returns:
        Flask application instance
    """
    global _daemon_cached_app, _daemon_boot_logged
    if _daemon_quiet() and _daemon_cached_app is not None:
        return _daemon_cached_app

    try:
        from backend.services import unified_points_sync
        unified_points_sync._app_creation_in_progress = True
    except Exception:
        pass
    try:
        if _daemon_quiet():
            with _daemon_init_lock:
                if _daemon_cached_app is not None:
                    return _daemon_cached_app
                import contextlib
                import io

                with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    app = _create_app_impl(config_name)
                _daemon_cached_app = app
                if not _daemon_boot_logged:
                    _daemon_boot_logged = True
                    print("[daemon] Flask app loaded (quiet mode — blueprint logs suppressed)", flush=True)
                return app
        return _create_app_impl(config_name)
    finally:
        try:
            from backend.services import unified_points_sync
            unified_points_sync._app_creation_in_progress = False
        except Exception:
            pass


def _create_app_impl(config_name=None):
    """Inner implementation of create_app (no re-entry guard)."""
    _project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # static_folder=None so /static/ is served by all_page_routes (merged root static/), not default app static
    # template_folder: backend/templates (debugger/index.html, api_debugger.html, etc.) for render_template()
    _flask_templates = os.path.join(_project_root, 'backend', 'templates')
    _flask_kw = {'static_folder': None}
    if os.path.isdir(_flask_templates):
        _flask_kw['template_folder'] = _flask_templates
    app = Flask(__name__, **_flask_kw)

    # Trust X-Forwarded-Proto/Host when behind nginx (avoids "too many redirects": redirects stay https)
    try:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    except Exception:
        pass

    # Load configuration from environment
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    # Session for account binding (login/create stores user_id)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 30  # 30 days

    # Database configuration: resolve SQLite to absolute path so the file can always be opened
    _instance_dir = os.path.join(_project_root, 'instance')
    # Ensure instance dir exists and is writable; fallback to cwd or temp if needed
    try:
        os.makedirs(_instance_dir, exist_ok=True)
        _test = os.path.join(_instance_dir, '.write_test')
        with open(_test, 'w'):
            pass
        os.remove(_test)
    except OSError:
        _cwd_instance = os.path.join(os.getcwd(), 'instance')
        try:
            os.makedirs(_cwd_instance, exist_ok=True)
            _instance_dir = _cwd_instance
        except OSError:
            import tempfile
            _instance_dir = os.path.join(tempfile.gettempdir(), 'masternoder_instance')
            os.makedirs(_instance_dir, exist_ok=True)
            print(f"Warning: Using temp directory for SQLite: {_instance_dir}")

    database_url = os.getenv('DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
    if database_url and database_url.startswith('sqlite:///'):
        path_part = database_url.replace('sqlite:///', '').lstrip('/').replace('/', os.sep)
        is_absolute = os.path.isabs(path_part) or (len(path_part) >= 2 and path_part[1] == ':')
        if not is_absolute:
            db_name = 'database.db' if 'database.db' in path_part else os.path.basename(path_part)
            db_path = os.path.join(_instance_dir, db_name)
            database_url = 'sqlite:///' + os.path.abspath(db_path).replace('\\', '/')
    if not database_url:
        db_path = os.path.join(_instance_dir, 'database.db')
        database_url = 'sqlite:///' + os.path.abspath(db_path).replace('\\', '/')

    # Ensure parent dir of the actual db file exists (handles subdirs in path)
    _db_path_abs = database_url.replace('sqlite:///', '').lstrip('/').replace('/', os.sep)
    if not os.path.isabs(_db_path_abs):
        _db_path_abs = os.path.abspath(_db_path_abs)
    _db_dir = os.path.dirname(_db_path_abs)
    if _db_dir:
        os.makedirs(_db_dir, exist_ok=True)

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url

    # Initialize database
    db.init_app(app)

    # Create all tables (safe: uses CREATE TABLE IF NOT EXISTS)
    with app.app_context():
        try:
            from src.db.models import (UserAccount, UserProfile, PlayerLevel, UserPoints,
                                       XpHistory, SystemPointSnapshot, ShopItem, UserInventory,
                                       ShopPurchase, BattleMatch, UserStorage)
            db.create_all()
        except Exception as e:
            print(f"Warning: Could not create database tables: {e}")

    # CRITICAL: Register unified/monetization/progression routes FIRST via explicit loader
    try:
        from backend.route_loader import register_unified_monetization_progression_routes, ensure_project_root_on_path
        ensure_project_root_on_path()
        register_unified_monetization_progression_routes(app)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"CRITICAL: unified/monetization/progression routes failed: {e}")
        # Fallback: direct import
        try:
            from backend.routes.missing_endpoints_routes import missing_endpoints_bp
            app.register_blueprint(missing_endpoints_bp)
        except Exception as e2:
            print(f"CRITICAL: missing_endpoints fallback also failed: {e2}")

    # Register blueprints (ensure imports are attempted; fallback to critical blueprints on failure)
    try:
        from backend.register_blueprints import register_all_blueprints
        register_all_blueprints(app)
    except ImportError as e:
        print(f"Warning: Could not import register_blueprints: {e}")
        _register_critical_blueprints(app)
    except Exception as e:
        print(f"Warning: Could not register blueprints: {e}")
        import traceback
        traceback.print_exc()
        _register_critical_blueprints(app)

    # Final pass: ensure unified/monetization/progression routes are registered (in case register_blueprints skipped)
    try:
        from backend.route_loader import register_unified_monetization_progression_routes
        register_unified_monetization_progression_routes(app)
    except Exception:
        pass  # Already registered or unrecoverable

    # Register skip-api-for-pages first so all page/static requests skip API middleware (same fix for all sites)
    try:
        from backend.middleware.skip_api_for_pages_middleware import register_skip_api_for_pages_middleware
        register_skip_api_for_pages_middleware(app)
    except Exception as e:
        print(f"Warning: Could not register skip-api-for-pages middleware: {e}")

    # Register auto-fix 404 middleware
    try:
        from backend.middleware.auto_fix_404_middleware import register_auto_fix_middleware
        register_auto_fix_middleware(app)
    except Exception as e:
        # Don't fail app creation if middleware registration fails
        print(f"Warning: Could not register auto-fix middleware: {e}")
    
    # Register JSON error handlers
    try:
        from backend.middleware.json_error_handler import register_json_error_handlers
        register_json_error_handlers(app)
    except Exception as e:
        # Don't fail app creation if error handler registration fails
        print(f"Warning: Could not register JSON error handlers: {e}")
    
    # Register error logging middleware
    try:
        from backend.middleware.error_logging_middleware import register_error_logging_middleware
        register_error_logging_middleware(app)
    except Exception as e:
        # Don't fail app creation if error logging registration fails
        print(f"Warning: Could not register error logging middleware: {e}")
    
    # Register rate limiting
    try:
        from backend.middleware.rate_limit_middleware import register_rate_limit_middleware
        register_rate_limit_middleware(app)
    except Exception as e:
        print(f"Warning: Could not register rate limit middleware: {e}")
    
    # Register signal processor middleware
    try:
        from backend.middleware.signal_processor_middleware import register_signal_processor_middleware
        register_signal_processor_middleware(app)
    except Exception as e:
        print(f"Warning: Could not register signal processor middleware: {e}")

    # Register AI user lifecycle middleware (auto-detect, auto-save, returning/dormant handling)
    try:
        from backend.middleware.ai_user_lifecycle_middleware import register_ai_user_lifecycle_middleware
        register_ai_user_lifecycle_middleware(app)
    except Exception as e:
        print(f"Warning: Could not register AI user lifecycle middleware: {e}")

    return app
