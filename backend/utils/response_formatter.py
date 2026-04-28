"""
Standardized Response Formatter
Ensures consistent API response format across all endpoints
"""
from flask import jsonify
from typing import Any, Optional, Dict
from datetime import datetime


class ResponseFormatter:
    """Standardized response formatting for API endpoints"""
    
    @staticmethod
    def success(data: Any = None, 
                message: Optional[str] = None,
                meta: Optional[Dict] = None,
                implementation_status: Optional[str] = None) -> tuple:
        """
        Format successful response
        
        Args:
            data: Response data
            message: Optional success message
            meta: Optional metadata (pagination, etc.)
            implementation_status: Optional status indicator
        """
        response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        if meta:
            response['meta'] = meta
        
        if implementation_status:
            response['implementation_status'] = implementation_status
        
        return jsonify(response), 200
    
    @staticmethod
    def created(data: Any = None, message: Optional[str] = None) -> tuple:
        """Format 201 Created response"""
        response = {
            'success': True,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        return jsonify(response), 201
    
    @staticmethod
    def accepted(data: Any = None, message: Optional[str] = None) -> tuple:
        """Format 202 Accepted response (async operations)"""
        response = {
            'success': True,
            'status': 'processing',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if data is not None:
            response['data'] = data
        
        if message:
            response['message'] = message
        
        return jsonify(response), 202
    
    @staticmethod
    def error(error: str,
              message: Optional[str] = None,
              code: Optional[str] = None,
              status_code: int = 400,
              details: Optional[Dict] = None) -> tuple:
        """
        Format error response
        
        Args:
            error: Error type/description
            message: Human-readable error message
            code: Error code for programmatic handling
            status_code: HTTP status code
            details: Additional error details
        """
        response = {
            'success': False,
            'error': error,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if message:
            response['message'] = message
        
        if code:
            response['code'] = code
        
        if details:
            response['details'] = details
        
        return jsonify(response), status_code
    
    @staticmethod
    def not_found(resource: str = 'Resource', message: Optional[str] = None) -> tuple:
        """Format 404 Not Found response"""
        return ResponseFormatter.error(
            error='Not Found',
            message=message or f'{resource} not found',
            code='NOT_FOUND',
            status_code=404
        )
    
    @staticmethod
    def unauthorized(message: Optional[str] = None) -> tuple:
        """Format 401 Unauthorized response"""
        return ResponseFormatter.error(
            error='Unauthorized',
            message=message or 'Authentication required',
            code='UNAUTHORIZED',
            status_code=401
        )
    
    @staticmethod
    def forbidden(message: Optional[str] = None) -> tuple:
        """Format 403 Forbidden response"""
        return ResponseFormatter.error(
            error='Forbidden',
            message=message or 'Access denied',
            code='FORBIDDEN',
            status_code=403
        )
    
    @staticmethod
    def rate_limit_exceeded(message: Optional[str] = None) -> tuple:
        """Format 429 Too Many Requests response"""
        return ResponseFormatter.error(
            error='Too Many Requests',
            message=message or 'Rate limit exceeded. Try again later.',
            code='RATE_LIMIT_EXCEEDED',
            status_code=429
        )
    
    @staticmethod
    def internal_error(message: Optional[str] = None, details: Optional[Dict] = None) -> tuple:
        """Format 500 Internal Server Error response"""
        return ResponseFormatter.error(
            error='Internal Server Error',
            message=message or 'An error occurred processing your request',
            code='INTERNAL_ERROR',
            status_code=500,
            details=details
        )
