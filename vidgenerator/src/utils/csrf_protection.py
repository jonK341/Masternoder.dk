"""
CSRF Protection utility for Flask
Provides CSRF token generation and validation
"""
import secrets
import hashlib
import hmac
from typing import Optional
from flask import request, session, g
from datetime import datetime, timedelta


class CSRFProtection:
    """CSRF token generation and validation"""
    
    @staticmethod
    def generate_token() -> str:
        """
        Generate a new CSRF token
        
        Returns:
            CSRF token string
        """
        token = secrets.token_urlsafe(32)
        return token
    
    @staticmethod
    def get_token() -> Optional[str]:
        """
        Get CSRF token from session or generate new one
        
        Returns:
            CSRF token string or None if session not available
        """
        if 'csrf_token' not in session:
            session['csrf_token'] = CSRFProtection.generate_token()
            session['csrf_token_time'] = datetime.utcnow().isoformat()
        return session.get('csrf_token')
    
    @staticmethod
    def validate_token(token: Optional[str] = None) -> bool:
        """
        Validate CSRF token
        
        Args:
            token: Token to validate (if None, reads from request)
        
        Returns:
            True if token is valid, False otherwise
        """
        if token is None:
            # Try to get token from header first, then form data
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
        
        if not token:
            return False
        
        session_token = session.get('csrf_token')
        if not session_token:
            return False
        
        # Use constant-time comparison to prevent timing attacks
        return hmac.compare_digest(token, session_token)
    
    @staticmethod
    def require_csrf_token():
        """
        Require CSRF token for current request (raises exception if invalid)
        
        Raises:
            ValueError: If CSRF token is missing or invalid
        """
        # Skip CSRF for GET, HEAD, OPTIONS (safe methods)
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return
        
        # Skip CSRF for API endpoints that use API keys (if configured)
        if request.path.startswith('/api/') and request.headers.get('X-API-Key'):
            # API key authentication bypasses CSRF
            return
        
        if not CSRFProtection.validate_token():
            # Log security event
            try:
                from src.utils.security_logger import SecurityLogger
                SecurityLogger.log_csrf_failure(request.path if request else None)
            except Exception:
                pass  # Don't fail if security logger unavailable
            
            raise ValueError('Invalid or missing CSRF token')


def csrf_protect(func):
    """
    Decorator to require CSRF token for a route
    
    Usage:
        @app.route('/api/endpoint', methods=['POST'])
        @csrf_protect
        def my_endpoint():
            return jsonify({'success': True})
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            CSRFProtection.require_csrf_token()
        except ValueError as e:
            from flask import jsonify
            return jsonify({
                'success': False,
                'error': str(e)
            }), 403
        
        return func(*args, **kwargs)
    
    return wrapper

