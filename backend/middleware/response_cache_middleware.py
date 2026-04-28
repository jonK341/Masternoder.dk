"""
Response Cache Middleware
Provides simple caching for API endpoints to reduce database load
"""
from functools import wraps
from flask import request, jsonify
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

# Simple in-memory cache (could be replaced with Redis in production)
_cache: Dict[str, Dict] = {}
_cache_ttl = {
    'default': 300,  # 5 minutes
    'stats': 180,    # 3 minutes
    'leaderboard': 120,  # 2 minutes
    'points': 60,    # 1 minute
}


def _get_cache_key(endpoint: str, params: dict) -> str:
    """Generate cache key from endpoint and parameters"""
    key_data = f"{endpoint}:{json.dumps(params, sort_keys=True)}"
    return hashlib.md5(key_data.encode()).hexdigest()


def _is_cacheable(endpoint: str) -> bool:
    """Check if endpoint should be cached"""
    cacheable_patterns = [
        '/api/stats/',
        '/api/game/stats',
        '/api/battle/stats',
        '/api/monetization/top50',
        '/api/points/comprehensive',
        '/api/points/all',
        '/api/frontpage/init',
        '/api/aggregator/',
        '/api/social/',
        '/api/star-map/25',
    ]
    return any(pattern in endpoint for pattern in cacheable_patterns)


def _get_cache_ttl(endpoint: str) -> int:
    """Get cache TTL for endpoint"""
    if '/stats/' in endpoint or '/game/stats' in endpoint:
        return _cache_ttl['stats']
    elif 'top50' in endpoint or 'leaderboard' in endpoint:
        return _cache_ttl['leaderboard']
    elif '/points/' in endpoint or '/points/all' in endpoint:
        return _cache_ttl['points']
    elif 'frontpage/init' in endpoint:
        return 30  # 30s for lightweight init
    elif '/social/' in endpoint:
        return 45  # 45s for social (user-scoped)
    elif '/star-map/25' in endpoint:
        return 60  # 60s for star map (mix of static and user-scoped)
    return _cache_ttl['default']


def cached_response(ttl: Optional[int] = None):
    """
    Decorator to cache endpoint responses
    
    Usage:
        @missing_endpoints_bp.route('/api/stats/summary')
        @cached_response(ttl=180)
        def stats_summary():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Only cache GET requests
            if request.method != 'GET':
                return func(*args, **kwargs)
            
            endpoint = request.path
            if not _is_cacheable(endpoint):
                return func(*args, **kwargs)
            
            # Generate cache key
            params = dict(request.args)
            cache_key = _get_cache_key(endpoint, params)
            
            # Check cache
            if cache_key in _cache:
                cached_data = _cache[cache_key]
                cache_time = cached_data.get('timestamp', datetime.min)
                cache_ttl_seconds = ttl or _get_cache_ttl(endpoint)
                
                if datetime.utcnow() - cache_time < timedelta(seconds=cache_ttl_seconds):
                    # Cache hit - return cached response
                    response = jsonify(cached_data['data'])
                    response.headers['X-Cache'] = 'HIT'
                    response.headers['X-Cache-Age'] = str(int((datetime.utcnow() - cache_time).total_seconds()))
                    return response
            
            # Cache miss - execute function and cache result
            result = func(*args, **kwargs)
            # Flask views may return (response, status) or (response, status, headers)
            if isinstance(result, tuple) and len(result) >= 1:
                response = result[0]
            else:
                response = result

            # Only cache successful JSON responses
            status = getattr(response, 'status_code', 200)
            if isinstance(result, tuple) and len(result) >= 2:
                status = result[1]
            if status == 200:
                try:
                    response_data = response.get_json() if callable(getattr(response, 'get_json', None)) else None
                    if response_data:
                        _cache[cache_key] = {
                            'data': response_data,
                            'timestamp': datetime.utcnow()
                        }
                        _cleanup_cache()
                        response.headers['X-Cache'] = 'MISS'
                except Exception:
                    pass

            return result
        
        return wrapper
    return decorator


def _cleanup_cache():
    """Remove expired cache entries"""
    global _cache
    now = datetime.utcnow()
    max_age = timedelta(hours=1)  # Keep entries for max 1 hour
    
    expired_keys = [
        key for key, value in _cache.items()
        if now - value.get('timestamp', datetime.min) > max_age
    ]
    
    for key in expired_keys:
        del _cache[key]


def clear_cache(endpoint: Optional[str] = None):
    """Clear cache for specific endpoint or all cache"""
    global _cache
    if endpoint:
        # Clear all entries for this endpoint
        keys_to_remove = [
            key for key in _cache.keys()
            if endpoint in key
        ]
        for key in keys_to_remove:
            del _cache[key]
    else:
        _cache.clear()


def get_cache_stats() -> Dict:
    """Get cache statistics"""
    return {
        'total_entries': len(_cache),
        'cache_size_mb': sum(len(str(v).encode()) for v in _cache.values()) / (1024 * 1024),
        'ttl_settings': _cache_ttl
    }
