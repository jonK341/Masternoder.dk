"""
Smart caching headers utility for Flask responses
Provides intelligent cache control based on content type and route patterns
"""
from flask import request, url_for
from typing import Optional
import os


class CacheHeaders:
    """Manage cache headers intelligently based on route and content type"""
    
    # API endpoints that should NEVER be cached (real-time data)
    NO_CACHE_APIS = [
        '/api/generator/create',
        '/api/documentary/progress/',
        '/api/generator/ai-clips/',
        '/api/statistics',
        '/api/stats/',
        '/api/game/state',
        '/api/documentary/video/',
        '/service-worker.js',  # Service workers should never be cached
    ]
    
    # API endpoints that can be cached for a short time (5 minutes)
    SHORT_CACHE_APIS = [
        '/api/categories/list',
        '/api/game/achievements',
        '/api/game/milestones',
        '/api/game/stats-points',
        '/api/game/categories',
    ]
    
    # Static file extensions that should be cached long-term
    STATIC_EXTENSIONS = [
        '.css', '.js', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.ico',
        '.woff', '.woff2', '.ttf', '.eot', '.mp4', '.webm', '.mp3', '.pdf'
    ]
    
    @staticmethod
    def should_no_cache(path: str) -> bool:
        """Check if path should have no-cache headers"""
        # Check API no-cache list
        for api_path in CacheHeaders.NO_CACHE_APIS:
            if api_path in path:
                return True
        return False
    
    @staticmethod
    def is_short_cache_api(path: str) -> bool:
        """Check if path should have short cache (5 minutes)"""
        for api_path in CacheHeaders.SHORT_CACHE_APIS:
            if api_path in path:
                return True
        return False
    
    @staticmethod
    def is_static_file(path: str) -> bool:
        """Check if path is a static file based on extension"""
        path_lower = path.lower()
        return any(path_lower.endswith(ext) for ext in CacheHeaders.STATIC_EXTENSIONS)
    
    @staticmethod
    def is_api_endpoint(path: str) -> bool:
        """Check if path is an API endpoint"""
        return path.startswith('/api/') or '/api/' in path
    
    @staticmethod
    def is_html_page(path: str) -> bool:
        """Check if path is an HTML page"""
        return (path.endswith('.html') or 
                path.endswith('/') or 
                (not CacheHeaders.is_api_endpoint(path) and 
                 not CacheHeaders.is_static_file(path)))
    
    @staticmethod
    def add_smart_cache_headers(response, max_age: Optional[int] = None):
        """
        Add intelligent cache headers to response based on path and content type
        
        Args:
            response: Flask response object
            max_age: Optional override for max-age (in seconds)
        """
        path = request.path
        
        # Service worker files should NEVER be cached (special case)
        if 'service-worker.js' in path:
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        
        # Allow explicit override via max_age parameter
        if max_age is not None:
            if max_age == 0:
                response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            else:
                response.headers['Cache-Control'] = f'public, max-age={max_age}, must-revalidate'
                response.headers['Expires'] = str(max_age)
            return response
        
        # No-cache APIs (real-time data)
        if CacheHeaders.should_no_cache(path):
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0, private'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            return response
        
        # Short-cache APIs (5 minutes - semi-static data like category lists)
        if CacheHeaders.is_short_cache_api(path):
            response.headers['Cache-Control'] = 'public, max-age=300, must-revalidate'  # 5 minutes
            response.headers['Expires'] = '300'
            return response
        
        # Static files (30 days - long-term cache with versioning)
        if CacheHeaders.is_static_file(path):
            response.headers['Cache-Control'] = 'public, max-age=2592000, immutable'  # 30 days
            response.headers['Expires'] = '2592000'
            # Don't add ETag for static files - let Apache handle it
            return response
        
        # HTML pages (15 minutes - allows updates but reduces server load)
        if CacheHeaders.is_html_page(path):
            response.headers['Cache-Control'] = 'public, max-age=900, must-revalidate'  # 15 minutes
            response.headers['Expires'] = '900'
            return response
        
        # Default: short cache for other content (5 minutes)
        response.headers['Cache-Control'] = 'public, max-age=300, must-revalidate'
        response.headers['Expires'] = '300'
        return response


def cache_control(max_age: Optional[int] = None):
    """
    Decorator to apply cache headers to a route
    
    Usage:
        @app.route('/api/data')
        @cache_control(max_age=300)  # Cache for 5 minutes
        def get_data():
            return jsonify({'data': 'value'})
    
    Args:
        max_age: Cache duration in seconds. None = auto-detect, 0 = no-cache
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            response = func(*args, **kwargs)
            if hasattr(response, 'headers'):
                CacheHeaders.add_smart_cache_headers(response, max_age=max_age)
            return response
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator

