"""
Error Logging Middleware
Logs errors to file and provides error tracking
"""
import os
import traceback
from datetime import datetime
from flask import request, jsonify
from typing import Optional
import json


class ErrorLogger:
    """Simple file-based error logger"""
    
    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(base_dir, 'logs', 'errors')
        
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
    
    def _get_log_file(self) -> str:
        """Get log file path for today"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        return os.path.join(self.log_dir, f'errors_{today}.log')
    
    def log_error(self, error: Exception, context: Optional[dict] = None):
        """Log error to file"""
        try:
            log_file = self._get_log_file()
            timestamp = datetime.utcnow().isoformat()
            
            error_data = {
                'timestamp': timestamp,
                'error_type': type(error).__name__,
                'error_message': str(error),
                'traceback': traceback.format_exc(),
                'request_path': request.path if request else None,
                'request_method': request.method if request else None,
                'request_args': dict(request.args) if request else None,
                'context': context or {}
            }
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(error_data, indent=2))
                f.write('\n' + '-' * 80 + '\n')
        except Exception as e:
            # Fallback to console if file logging fails
            print(f"Error logging failed: {e}")
            print(f"Original error: {error}")


# Global error logger instance
error_logger = ErrorLogger()


def register_error_logging_middleware(app):
    """Register error logging middleware with Flask app"""
    
    def _api_500_payload(e):
        payload = {
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An error occurred processing your request'
        }
        if os.environ.get("FLASK_DEBUG", "").strip().lower() in ("1", "true", "yes"):
            payload['detail'] = str(e)
        elif request.args.get("debug", "").strip() in ("1", "true"):
            payload['detail'] = str(e)
        return payload

    @app.errorhandler(500)
    def handle_500_error(e):
        """Handle 500 Internal Server Error"""
        error_logger.log_error(e, {
            'status_code': 500,
            'endpoint': request.path
        })
        if request.path.startswith('/api/'):
            return jsonify(_api_500_payload(e)), 500
        return jsonify(_api_500_payload(e)), 500
    
    @app.errorhandler(404)
    def handle_404_error(e):
        """Handle 404 Not Found. API paths delegate to auto-fix (must not return None)."""
        if '/api/' in request.path:
            try:
                from backend.middleware.auto_fix_404_middleware import handle_404
                return handle_404(e)
            except Exception:
                return jsonify({
                    'success': False,
                    'error': 'Not Found',
                    'path': request.path,
                    'method': request.method,
                }), 404

        error_logger.log_error(e, {
            'status_code': 404,
            'endpoint': request.path
        })
        return e
    
    @app.errorhandler(Exception)
    def handle_generic_error(e):
        """Handle any unhandled exception"""
        error_logger.log_error(e, {
            'endpoint': request.path,
            'method': request.method
        })
        
        # Return JSON error for API endpoints
        if '/api/' in request.path:
            payload = _api_500_payload(e)
            payload['message'] = 'An unexpected error occurred'
            return jsonify(payload), 500
        
        # Re-raise for non-API endpoints
        raise e
