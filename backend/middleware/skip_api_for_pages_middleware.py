"""
Skip API-only middleware for page and static requests.
Runs first so all sites (/, /vidgenerator/*, static, etc.) avoid any API middleware work.
"""
from flask import request, g

_API_PATH_MARKER = "/api/"


def _is_api_request():
    """True if this request is for an API endpoint (needs rate limit, lifecycle, signal processing)."""
    path = request.path
    return _API_PATH_MARKER in path


def register_skip_api_for_pages_middleware(app):
    """Register before_request that marks non-API requests so other middleware can skip."""
    @app.before_request
    def _mark_non_api():
        if not _is_api_request():
            g.skip_api_middleware = True
        else:
            g.skip_api_middleware = False
