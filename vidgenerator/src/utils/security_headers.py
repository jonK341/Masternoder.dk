"""
Security headers utility for Flask
Provides security headers like CSP, HSTS, X-Frame-Options, etc.
"""
from flask import request, Response
from typing import Optional
import os

class SecurityHeaders:
    """Manage security headers for Flask responses"""
    
    @staticmethod
    def add_security_headers(response: Response) -> Response:
        """
        Add security headers to Flask response
        
        Args:
            response: Flask response object
        
        Returns:
            Response with security headers added
        """
        # Content Security Policy (CSP)
        # Allow same-origin and common CDNs, block inline scripts/styles by default
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "  # unsafe-inline/eval needed for inline scripts in HTML, added cdn.jsdelivr.net for chart.js
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; "  # Allow Font Awesome and chart.js from CDN
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net data:; "  # Allow Font Awesome fonts and chart.js fonts
            "img-src 'self' data: https:; "
            "media-src 'self' data:; "
            "connect-src 'self' https:; "
            "frame-ancestors 'self'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        response.headers['Content-Security-Policy'] = csp_policy
        
        # HTTP Strict Transport Security (HSTS) - only on HTTPS
        try:
            from flask import has_request_context
            if has_request_context():
                if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
                    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        except Exception:
            # If we can't determine, don't add HSTS
            pass
        
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Prevent MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Enable XSS protection (legacy, but still useful)
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        # Removed 'speaker' and 'vibrate' as they are deprecated/unrecognized features
        permissions_policy = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "fullscreen=(self), "
            "picture-in-picture=()"
        )
        response.headers['Permissions-Policy'] = permissions_policy
        
        # Remove server header if present (Flask doesn't add it by default)
        # But we'll ensure it's not exposed
        if 'Server' in response.headers:
            del response.headers['Server']
        
        return response
    
    @staticmethod
    def add_csrf_token_header(response: Response, token: Optional[str] = None) -> Response:
        """
        Add CSRF token to response header (for JavaScript to read)
        
        Args:
            response: Flask response object
            token: Optional CSRF token (if None, won't add header)
        
        Returns:
            Response with CSRF token header if token provided
        """
        if token:
            response.headers['X-CSRF-Token'] = token
        return response

