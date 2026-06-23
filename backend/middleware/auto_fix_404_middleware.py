"""
Auto-Fix 404 Middleware
Intercepts 404 errors, logs for Register Intelligence, and auto-fixes when possible.
"""
from flask import request, jsonify
from backend.services.auto_fix_endpoints import auto_fix_endpoints


def _log_404_for_register_intelligence(path: str, method: str):
    """Log 404 to Register Intelligence (non-blocking)."""
    try:
        from backend.services.register_intelligence.missing_route_resolver import MissingRouteResolver
        MissingRouteResolver().log_404(path, method)
    except Exception:
        pass


def handle_404(e):
    """Handle 404 errors and auto-fix if possible"""
    path = request.path
    method = request.method
    
    # Skip static files and known non-API paths
    if any(skip in path for skip in ['/static/', '/uploads/', '/output/', '.css', '.js', '.png', '.jpg', '.ico']):
        return e  # Let Flask handle it normally
    
    # Always return JSON for API endpoints
    if '/api/' in path:
        _log_404_for_register_intelligence(path, method)
        # Try to auto-fix
        response_data, status_code = auto_fix_endpoints.auto_fix_endpoint(path, method)
        
        if response_data and status_code:
            return jsonify(response_data), status_code
        
        # If not auto-fixed, return JSON 404
        return jsonify({
            'success': False,
            'error': 'Not Found',
            'path': path,
            'method': method,
            'message': 'Endpoint not found. Logged for Register Intelligence.'
        }), 404
    
    # For non-API paths, keep Flask's normal 404 response.
    return e

def register_auto_fix_middleware(app):
    """Register auto-fix middleware with Flask app"""
    app.register_error_handler(404, handle_404)
    return app
