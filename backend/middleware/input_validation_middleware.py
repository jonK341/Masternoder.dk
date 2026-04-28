"""
Input Validation Middleware
Validates and sanitizes API request inputs
"""
from flask import request, jsonify
import re
from typing import Optional, Dict, Any, List, Tuple


class InputValidator:
    """Input validation and sanitization utilities"""
    
    @staticmethod
    def sanitize_string(value: Any, max_length: int = 1000) -> str:
        """Sanitize string input"""
        if value is None:
            return ''
        value = str(value).strip()
        if len(value) > max_length:
            value = value[:max_length]
        # Remove potentially dangerous characters
        value = re.sub(r'[<>"\']', '', value)
        return value
    
    @staticmethod
    def validate_length(value: str, min_length: int = 0, max_length: int = 1000) -> bool:
        """Validate string length"""
        if not isinstance(value, str):
            return False
        return min_length <= len(value) <= max_length
    
    @staticmethod
    def validate_required(data: Dict, required_fields: List[str]) -> tuple[bool, Optional[str]]:
        """Validate required fields are present"""
        missing = [field for field in required_fields if field not in data or data[field] is None]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        return True, None
    
    @staticmethod
    def validate_integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None) -> Tuple[bool, Optional[int], Optional[str]]:
        """Validate and convert to integer"""
        try:
            int_val = int(value)
            if min_val is not None and int_val < min_val:
                return False, None, f"Value must be >= {min_val}"
            if max_val is not None and int_val > max_val:
                return False, None, f"Value must be <= {max_val}"
            return True, int_val, None
        except (ValueError, TypeError):
            return False, None, "Invalid integer value"
    
    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user_id format"""
        if not user_id or not isinstance(user_id, str):
            return False
        # Allow alphanumeric, underscore, hyphen, max 100 chars
        return bool(re.match(r'^[a-zA-Z0-9_-]{1,100}$', user_id))
    
    @staticmethod
    def sanitize_json_data(data: Dict) -> Dict:
        """Sanitize all string values in JSON data"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = InputValidator.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = InputValidator.sanitize_json_data(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    InputValidator.sanitize_json_data(item) if isinstance(item, dict)
                    else InputValidator.sanitize_string(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


def validate_api_input(required_fields: Optional[List[str]] = None, 
                       integer_fields: Optional[Dict[str, Dict]] = None):
    """
    Decorator to validate API input
    
    Usage:
        @validate_api_input(required_fields=['user_id'], integer_fields={'days': {'min': 1, 'max': 365}})
        def my_endpoint():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Validate JSON body for POST/PUT requests
            if request.method in ['POST', 'PUT', 'PATCH']:
                data = request.get_json() or {}
                
                # Validate required fields
                if required_fields:
                    is_valid, error_msg = InputValidator.validate_required(data, required_fields)
                    if not is_valid:
                        return jsonify({
                            'success': False,
                            'error': error_msg,
                            'code': 'VALIDATION_ERROR'
                        }), 400
                
                # Validate integer fields
                if integer_fields:
                    for field, constraints in integer_fields.items():
                        if field in data:
                            is_valid, value, error_msg = InputValidator.validate_integer(
                                data[field],
                                min_val=constraints.get('min'),
                                max_val=constraints.get('max')
                            )
                            if not is_valid:
                                return jsonify({
                                    'success': False,
                                    'error': f"{field}: {error_msg}",
                                    'code': 'VALIDATION_ERROR'
                                }), 400
                            data[field] = value
                
                # Sanitize all string values
                data = InputValidator.sanitize_json_data(data)
                request.validated_data = data
            
            # Validate query parameters
            if request.method == 'GET':
                # Validate user_id if present
                user_id = request.args.get('user_id')
                if user_id and not InputValidator.validate_user_id(user_id):
                    return jsonify({
                        'success': False,
                        'error': 'Invalid user_id format',
                        'code': 'VALIDATION_ERROR'
                    }), 400
                
                # Validate integer query params
                if integer_fields:
                    for field, constraints in integer_fields.items():
                        value = request.args.get(field)
                        if value:
                            is_valid, int_value, error_msg = InputValidator.validate_integer(
                                value,
                                min_val=constraints.get('min'),
                                max_val=constraints.get('max')
                            )
                            if not is_valid:
                                return jsonify({
                                    'success': False,
                                    'error': f"{field}: {error_msg}",
                                    'code': 'VALIDATION_ERROR'
                                }), 400
            
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


def register_input_validation_middleware(app):
    """Register input validation middleware (optional - can be used via decorator)"""
    # Middleware is applied via decorator, no global registration needed
    pass
