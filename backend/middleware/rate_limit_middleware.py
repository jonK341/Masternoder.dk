"""
Rate Limit Middleware
Simple in-memory rate limiting for API endpoints
"""
from flask import request, jsonify, g
from datetime import datetime, timedelta
from collections import defaultdict
import threading

_store = defaultdict(list)
_lock = threading.Lock()

# Endpoint-specific limits: (requests_per_window, window_seconds)
_LIMITS = {
    '/api/mn2/withdraw': (5, 60),
    '/api/user/login': (12, 60),
    '/api/user/security/verify': (20, 60),
    '/api/generator/create': (10, 60),
    '/api/generator/ai-clips': (20, 60),
    '/api/ai-clips/generate': (20, 60),
    '/api/documentary/restart': (5, 60),
    '/api/video-generation/calculate': (30, 60),
    '/api/auth/': (30, 60),
    '/api/auth/': (30, 60),
    'default': (120, 60),  # 120 req/min for generic API
}


def _get_limit(path: str):
    for prefix, lim in _LIMITS.items():
        if prefix != 'default' and path.startswith(prefix):
            return lim
    return _LIMITS['default']


def _check_rate_limit(key: str, limit: int, window_sec: int) -> bool:
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_sec)
    with _lock:
        _store[key] = [t for t in _store[key] if t > cutoff]
        if len(_store[key]) >= limit:
            return False
        _store[key].append(now)
    return True


def register_rate_limit_middleware(app):
    """Register rate limit middleware with Flask app"""
    def _before():
        if getattr(g, "skip_api_middleware", False):
            return None
        path = request.path
        if '/api/' not in path:
            return None
        limit, window = _get_limit(path)
        key = f"{request.remote_addr}:{path}"
        if not _check_rate_limit(key, limit, window):
            return jsonify({
                'success': False,
                'error': 'Too Many Requests',
                'message': f'Rate limit exceeded. Try again later.'
            }), 429
        return None

    app.before_request(_before)
