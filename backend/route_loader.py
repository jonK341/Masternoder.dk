"""
Explicit route loader - imports and registers all critical API routes.
Use when PYTHONPATH or import path issues prevent routes from being registered.
"""
import os
import sys


def ensure_project_root_on_path():
    """Ensure project root is on sys.path so backend.* and src.* imports work."""
    # Try multiple strategies to find project root
    candidates = []
    # Strategy 1: from src/app (this file is backend/route_loader.py, so go up 1 to project root)
    _this = os.path.abspath(__file__)
    _backend = os.path.dirname(_this)
    _root1 = os.path.dirname(_backend)
    if os.path.isdir(os.path.join(_root1, "backend")) and os.path.isdir(os.path.join(_root1, "src")):
        candidates.append(_root1)
    # Strategy 2: if we're inside vidgenerator/, go to parent
    parts = _this.replace("\\", "/").split("/")
    if "vidgenerator" in parts:
        idx = parts.index("vidgenerator")
        parent_parts = parts[:idx]
        _root2 = os.path.join(*parent_parts) if parent_parts else os.path.sep
        if _root2 and os.path.isdir(os.path.join(_root2, "backend")):
            candidates.append(_root2)
    for root in candidates:
        if root and root not in sys.path:
            sys.path.insert(0, root)
            os.environ["PYTHONPATH"] = root + os.pathsep + os.environ.get("PYTHONPATH", "")
            return root
    return None


def register_unified_monetization_progression_routes(app):
    """
    Register all_pages first (so /vidgenerator/generator, profile, etc. work), then missing_endpoints.
    missing_endpoints contains: unified/status, monetization/top-50, progression/all, etc.
    """
    ensure_project_root_on_path()
    # Register all_pages first so page routes take precedence
    try:
        from backend.routes.all_page_routes import all_page_bp
        if "all_pages" not in app.blueprints:
            app.register_blueprint(all_page_bp)
    except Exception:
        pass
    try:
        from backend.routes.missing_endpoints_routes import missing_endpoints_bp
        if "missing_endpoints" not in app.blueprints:
            app.register_blueprint(missing_endpoints_bp)
            return True
        return True
    except ImportError as e:
        root = ensure_project_root_on_path()
        if root:
            try:
                from backend.routes.missing_endpoints_routes import missing_endpoints_bp
                if "missing_endpoints" not in app.blueprints:
                    app.register_blueprint(missing_endpoints_bp)
                return True
            except Exception:
                pass
        raise e
