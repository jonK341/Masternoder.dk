"""
Response compression middleware for Flask
Compresses responses using gzip or deflate
"""
from flask import request, Response, after_this_request
from functools import wraps
import gzip
import logging

logger = logging.getLogger('vidgenerator.compression')

# MIME types that should be compressed
COMPRESSIBLE_TYPES = [
    'text/html',
    'text/css',
    'text/javascript',
    'text/xml',
    'text/plain',
    'application/json',
    'application/javascript',
    'application/xml',
    'application/json',
    'application/x-javascript'
]


def should_compress(response: Response) -> bool:
    """
    Check if response should be compressed
    
    Args:
        response: Flask response object
    
    Returns:
        True if response should be compressed
    """
    # Check if client supports compression
    accept_encoding = request.headers.get('Accept-Encoding', '')
    if 'gzip' not in accept_encoding and 'deflate' not in accept_encoding:
        return False
    
    # Check content type
    content_type = response.content_type or ''
    if not any(ct in content_type for ct in COMPRESSIBLE_TYPES):
        return False
    
    # Don't compress very small responses (overhead not worth it)
    if response.content_length and response.content_length < 200:
        return False
    
    # Don't compress if already compressed
    if 'Content-Encoding' in response.headers:
        return False
    
    return True


def compress_response(response: Response) -> Response:
    """
    Compress response using gzip
    
    Args:
        response: Flask response object
    
    Returns:
        Compressed response
    """
    if not should_compress(response):
        return response
    
    # Get response data
    data = response.get_data()
    
    # Compress with gzip
    compressed = gzip.compress(data, compresslevel=6)
    
    # Create new response with compressed data
    compressed_response = Response(
        compressed,
        status=response.status_code,
        headers=dict(response.headers)
    )
    
    # Set compression headers
    compressed_response.headers['Content-Encoding'] = 'gzip'
    compressed_response.headers['Content-Length'] = len(compressed)
    
    logger.debug(f"Compressed response: {len(data)} -> {len(compressed)} bytes ({len(compressed)/len(data)*100:.1f}%)")
    
    return compressed_response


def compression_enabled(func):
    """
    Decorator to enable compression for a specific route
    
    Usage:
        @app.route('/api/data')
        @compression_enabled
        def get_data():
            return jsonify({'data': 'value'})
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        @after_this_request
        def compress(response):
            return compress_response(response)
        
        return func(*args, **kwargs)
    
    return wrapper

