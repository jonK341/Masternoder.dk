"""
API Utilities - Helper functions for API endpoints
"""

from datetime import datetime

def validate_api_key(api_key: str) -> bool:
    """Validate API key format"""
    if not api_key or len(api_key) < 10:
        return False
    return True

def format_api_response(data: dict, success: bool = True) -> dict:
    """Format standardized API response"""
    return {
        'success': success,
        'data': data if success else None,
        'error': None if success else data,
        'timestamp': datetime.now().isoformat()
    }

