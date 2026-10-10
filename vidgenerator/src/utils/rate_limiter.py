"""
Rate limiting utility for Flask routes
Provides simple in-memory rate limiting
"""
import time
from collections import defaultdict
from typing import Optional
from flask import request, jsonify, g
import logging

logger = logging.getLogger('vidgenerator.ratelimit')


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        """Initialize rate limiter"""
        # Store: {identifier: [(timestamp, ...), ...]}
        self.requests = defaultdict(list)
        self.limits = {}
    
    def add_limit(self, endpoint: str, max_requests: int, window: int):
        """
        Add rate limit for an endpoint
        
        Args:
            endpoint: Route endpoint pattern
            max_requests: Maximum requests allowed
            window: Time window in seconds
        """
        self.limits[endpoint] = {
            'max': max_requests,
            'window': window
        }
    
    def _get_identifier(self) -> str:
        """Get identifier for current request"""
        # Use IP address as identifier
        return request.remote_addr or 'unknown'
    
    def is_allowed(self, endpoint: str) -> tuple[bool, Optional[dict]]:
        """
        Check if request is allowed under rate limit
        
        Args:
            endpoint: Route endpoint
        
        Returns:
            Tuple of (is_allowed, rate_limit_info)
        """
        if endpoint not in self.limits:
            # No limit for this endpoint
            return True, None
        
        limit = self.limits[endpoint]
        identifier = self._get_identifier()
        key = f"{identifier}:{endpoint}"
        
        now = time.time()
        window_start = now - limit['window']
        
        # Clean old requests
        self.requests[key] = [
            ts for ts in self.requests[key] if ts > window_start
        ]
        
        # Check limit
        if len(self.requests[key]) >= limit['max']:
            # Rate limit exceeded
            remaining = 0
            reset_time = self.requests[key][0] + limit['window'] if self.requests[key] else now
            reset_in = int(reset_time - now)
            
            return False, {
                'limit': limit['max'],
                'remaining': remaining,
                'reset': int(reset_time),
                'reset_in': reset_in
            }
        
        # Allow request - record it
        self.requests[key].append(now)
        remaining = limit['max'] - len(self.requests[key])
        reset_time = self.requests[key][0] + limit['window'] if self.requests[key] else now + limit['window']
        
        return True, {
            'limit': limit['max'],
            'remaining': remaining,
            'reset': int(reset_time),
            'reset_in': int(reset_time - now)
        }
    
    def get_stats(self) -> dict:
        """Get rate limiter statistics"""
        return {
            'tracked_endpoints': len(self.limits),
            'active_keys': len(self.requests)
        }


# Global rate limiter instance
_rate_limiter = RateLimiter()

# Default rate limits
_rate_limiter.add_limit('/api/generator/create', max_requests=10, window=60)  # 10 requests per minute
_rate_limiter.add_limit('/api/statistics', max_requests=30, window=60)  # 30 requests per minute
_rate_limiter.add_limit('/api/stats/', max_requests=60, window=60)  # 60 requests per minute


def rate_limit(endpoint: Optional[str] = None):
    """
    Decorator to apply rate limiting to a route
    
    Usage:
        @app.route('/api/endpoint')
        @rate_limit(endpoint='/api/endpoint')
        def my_endpoint():
            return jsonify({'data': 'value'})
        
        # Or without endpoint (uses request.path):
        @app.route('/api/endpoint')
        @rate_limit()
        def my_endpoint():
            return jsonify({'data': 'value'})
    
    Args:
        endpoint: Optional endpoint identifier (defaults to request.path)
    """
    def decorator(func):
        from functools import wraps
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            endpoint_key = endpoint or request.path
            
            # If no limit configured, just execute (skip rate limiting)
            if endpoint_key not in _rate_limiter.limits:
                return func(*args, **kwargs)
            
            allowed, limit_info = _rate_limiter.is_allowed(endpoint_key)
            
            if not allowed:
                logger.warning(f"Rate limit exceeded for {endpoint_key} from {request.remote_addr}")
                
                # Log security event
                try:
                    from src.utils.security_logger import SecurityLogger
                    SecurityLogger.log_rate_limit_exceeded(endpoint_key, request.remote_addr)
                except Exception:
                    pass  # Don't fail if security logger unavailable
                
                response = jsonify({
                    'success': False,
                    'error': 'Rate limit exceeded. Please try again later.',
                    'rate_limit': limit_info
                })
                response.status_code = 429  # Too Many Requests
                
                # Add rate limit headers
                if limit_info:
                    response.headers['X-RateLimit-Limit'] = str(limit_info['limit'])
                    response.headers['X-RateLimit-Remaining'] = str(limit_info['remaining'])
                    response.headers['X-RateLimit-Reset'] = str(limit_info['reset'])
                
                return response
            
            # Store rate limit info in request context for logging
            g.rate_limit_info = limit_info
            
            return func(*args, **kwargs)
        
        return wrapper
    
    return decorator


def get_rate_limit_stats() -> dict:
    """Get rate limiter statistics"""
    return _rate_limiter.get_stats()

