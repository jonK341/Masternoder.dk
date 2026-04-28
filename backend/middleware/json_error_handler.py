"""
JSON Error Handler Middleware
Ensures all API endpoints return JSON even on error.
When FLASK_DEBUG=1 or request has debug=1, 500 responses include a "detail" field with the exception message.
"""
import os
import traceback
from flask import request, jsonify

def _include_error_detail():
    """True if we should include exception detail in API 500 responses (debug only)."""
    if os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes"):
        return True
    if request and request.args.get("debug", "").strip() in ("1", "true"):
        return True
    return False

def register_json_error_handlers(app):
    """Register JSON error handlers for all error codes"""
    
    @app.errorhandler(400)
    def bad_request(error):
        """Handle 400 Bad Request"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': str(error) if hasattr(error, 'description') else 'Invalid request',
                'path': request.path
            }), 400
        return error
    
    @app.errorhandler(401)
    def unauthorized(error):
        """Handle 401 Unauthorized"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Authentication required',
                'path': request.path
            }), 401
        return error
    
    @app.errorhandler(403)
    def forbidden(error):
        """Handle 403 Forbidden"""
        if request.path.startswith('/api/'):
            return jsonify({
                'success': False,
                'error': 'Forbidden',
                'message': 'Access denied',
                'path': request.path
            }), 403
        return error
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server Error"""
        if request.path.startswith('/api/'):
            payload = {
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An error occurred processing your request',
                'path': request.path
            }
            if _include_error_detail():
                payload['detail'] = str(error)
            return jsonify(payload), 500
        return error
    
    @app.errorhandler(TypeError)
    def view_returned_none(error):
        """Handle view functions that returned None (no valid response)."""
        msg = str(error) if error else ''
        if 'did not return a valid response' in msg or 'returned None' in msg:
            if request and request.path.startswith('/api/'):
                return jsonify({
                    'success': False,
                    'error': 'Internal Server Error',
                    'message': 'The request could not be completed.',
                    'path': request.path
                }), 500
        raise error

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all unhandled exceptions"""
        if request.path.startswith('/api/'):
            try:
                import logging
                logging.error(f"Unhandled exception in API: {str(error)}")
                logging.error(traceback.format_exc())
            except Exception:
                pass
            payload = {
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred',
                'path': request.path
            }
            if _include_error_detail():
                payload['detail'] = str(error)
            return jsonify(payload), 500
        raise error
    
    return app
