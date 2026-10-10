"""
Input validation and sanitization utilities
Provides comprehensive input validation and sanitization
"""
import re
import html
from typing import Optional, List, Dict, Any
from urllib.parse import quote, unquote


class InputValidator:
    """Input validation and sanitization"""
    
    # Dangerous patterns to detect
    DANGEROUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # Script tags
        r'javascript:',  # JavaScript protocol
        r'on\w+\s*=',  # Event handlers (onclick, onerror, etc.)
        r'<iframe[^>]*>',  # Iframe tags
        r'<object[^>]*>',  # Object tags
        r'<embed[^>]*>',  # Embed tags
        r'<link[^>]*>',  # Link tags
        r'<meta[^>]*>',  # Meta tags
    ]
    
    @staticmethod
    def sanitize_string(value: str, max_length: Optional[int] = None, allow_html: bool = False) -> str:
        """
        Sanitize a string input
        
        Args:
            value: Input string
            max_length: Maximum length (None for no limit)
            allow_html: Whether to allow HTML (if False, escapes HTML)
        
        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Strip whitespace
        value = value.strip()
        
        # Check for dangerous patterns
        if not allow_html:
            # Escape HTML entities
            value = html.escape(value)
            
            # Remove any remaining dangerous patterns
            for pattern in InputValidator.DANGEROUS_PATTERNS:
                value = re.sub(pattern, '', value, flags=re.IGNORECASE | re.DOTALL)
        
        # Limit length
        if max_length and len(value) > max_length:
            value = value[:max_length]
        
        return value
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email address format
        
        Args:
            email: Email address to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
        
        # Basic email regex
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> bool:
        """
        Validate URL format and scheme
        
        Args:
            url: URL to validate
            allowed_schemes: List of allowed schemes (default: ['http', 'https'])
        
        Returns:
            True if valid, False otherwise
        """
        if not url or not isinstance(url, str):
            return False
        
        if allowed_schemes is None:
            allowed_schemes = ['http', 'https']
        
        # Check if URL starts with allowed scheme
        url_lower = url.lower().strip()
        for scheme in allowed_schemes:
            if url_lower.startswith(f'{scheme}://'):
                return True
        
        return False
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename to prevent directory traversal and other attacks
        
        Args:
            filename: Filename to sanitize
        
        Returns:
            Sanitized filename
        """
        if not isinstance(filename, str):
            filename = str(filename)
        
        # Remove path components
        filename = filename.replace('..', '').replace('/', '').replace('\\', '')
        
        # Remove dangerous characters
        filename = re.sub(r'[<>:"|?*]', '', filename)
        
        # Limit length
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename.strip()
    
    @staticmethod
    def validate_integer(value: Any, min_value: Optional[int] = None, max_value: Optional[int] = None) -> Optional[int]:
        """
        Validate and convert to integer
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        
        Returns:
            Integer value or None if invalid
        """
        try:
            int_value = int(value)
            
            if min_value is not None and int_value < min_value:
                return None
            
            if max_value is not None and int_value > max_value:
                return None
            
            return int_value
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_float(value: Any, min_value: Optional[float] = None, max_value: Optional[float] = None) -> Optional[float]:
        """
        Validate and convert to float
        
        Args:
            value: Value to validate
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        
        Returns:
            Float value or None if invalid
        """
        try:
            float_value = float(value)
            
            if min_value is not None and float_value < min_value:
                return None
            
            if max_value is not None and float_value > max_value:
                return None
            
            return float_value
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def validate_choice(value: Any, choices: List[Any]) -> bool:
        """
        Validate that value is in allowed choices
        
        Args:
            value: Value to validate
            choices: List of allowed choices
        
        Returns:
            True if value is in choices, False otherwise
        """
        return value in choices
    
    @staticmethod
    def sanitize_json(data: Dict[str, Any], max_depth: int = 10) -> Dict[str, Any]:
        """
        Recursively sanitize JSON data
        
        Args:
            data: JSON data to sanitize
            max_depth: Maximum recursion depth
        
        Returns:
            Sanitized JSON data
        """
        if max_depth <= 0:
            return {}
        
        if isinstance(data, dict):
            return {
                InputValidator.sanitize_string(str(k)): InputValidator.sanitize_json(v, max_depth - 1)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [InputValidator.sanitize_json(item, max_depth - 1) for item in data]
        elif isinstance(data, str):
            return InputValidator.sanitize_string(data)
        else:
            return data
    
    @staticmethod
    def get_json_safe(default: Any = None):
        """
        Safely get JSON from Flask request
        
        Args:
            default: Default value if JSON parsing fails
        
        Returns:
            Parsed JSON data or default
        """
        from flask import request
        try:
            data = request.get_json(silent=True) or {}
            # Sanitize the JSON data
            return InputValidator.sanitize_json(data)
        except Exception:
            return default if default is not None else {}
    
    @staticmethod
    def validate_required(data: Dict[str, Any], required_fields: List[str]) -> tuple[bool, Optional[str]]:
        """
        Validate that required fields are present
        
        Args:
            data: Data dictionary to validate
            required_fields: List of required field names
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        missing = [field for field in required_fields if field not in data or not data[field]]
        if missing:
            return False, f"Missing required fields: {', '.join(missing)}"
        return True, None
    
    @staticmethod
    def validate_length(value: str, min_length: Optional[int] = None, max_length: Optional[int] = None) -> bool:
        """
        Validate string length
        
        Args:
            value: String to validate
            min_length: Minimum length (None for no minimum)
            max_length: Maximum length (None for no maximum)
        
        Returns:
            True if length is valid, False otherwise
        """
        if not isinstance(value, str):
            return False
        
        length = len(value)
        
        if min_length is not None and length < min_length:
            return False
        
        if max_length is not None and length > max_length:
            return False
        
        return True
