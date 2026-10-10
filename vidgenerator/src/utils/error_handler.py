"""
Professional error handler for user-friendly error messages
"""
from typing import Dict, Optional
import uuid
import logging
from flask import request

logger = logging.getLogger('vidgenerator.errors')


class ErrorHandler:
    """Handles errors and converts them to user-friendly messages"""
    
    # Map technical errors to user-friendly messages
    ERROR_MESSAGES = {
        # API/Network errors
        'ConnectionError': 'Kunne ikke oprette forbindelse til videogenereringstjenesten. Prøv igen om et øjeblik.',
        'TimeoutError': 'Anmodningen tog for lang tid. Prøv igen med en kortere video eller kontakt support.',
        'requests.exceptions.ConnectionError': 'Kunne ikke oprette forbindelse til videogenereringstjenesten.',
        'requests.exceptions.Timeout': 'Anmodningen tog for lang tid. Prøv igen.',
        
        # API Key errors
        'API key not configured': 'Videogenereringstjenesten er ikke konfigureret korrekt. Kontakt administratoren.',
        'API key not configured': 'API-nøgle mangler. Kontakt support.',
        '401': 'API-nøgle er ugyldig. Kontakt support.',
        '403': 'Adgang nægtet. Kontakt support.',
        
        # Video generation errors
        'No video generation providers available': 'Ingen videogenereringstjenester er tilgængelige. Prøv igen senere.',
        'Video compilation failed': 'Videoen kunne ikke kompileres. Prøv igen eller kontakt support.',
        'FFmpeg not found': 'Video-processor mangler. Kontakt support.',
        
        # File errors
        'FileNotFoundError': 'En fil kunne ikke findes. Prøv igen.',
        'PermissionError': 'Der er ikke adgang til at gemme filen. Kontakt support.',
        'No space left on device': 'Der er ikke plads tilbage. Kontakt support.',
        
        # Generic errors
        'ModuleNotFoundError': 'Systemet mangler en påkrævet komponent. Kontakt support.',
        'ImportError': 'Systemet mangler en påkrævet komponent. Kontakt support.',
    }
    
    # Error categories for better handling
    CATEGORY_MAPPINGS = {
        'connection': ['ConnectionError', 'requests.exceptions.ConnectionError', 'TimeoutError'],
        'api_key': ['API key', '401', '403'],
        'video_generation': ['video generation', 'Video compilation', 'FFmpeg'],
        'file': ['FileNotFoundError', 'PermissionError', 'No space'],
        'system': ['ModuleNotFoundError', 'ImportError'],
    }
    
    @staticmethod
    def get_user_friendly_message(error: Exception, fallback_message: str = None) -> str:
        """
        Convert technical error to user-friendly message
        
        Args:
            error: Exception object or error string
            fallback_message: Custom fallback message
        
        Returns:
            User-friendly error message
        """
        error_str = str(error)
        error_type = type(error).__name__
        
        # Check exact matches first
        if error_str in ErrorHandler.ERROR_MESSAGES:
            return ErrorHandler.ERROR_MESSAGES[error_str]
        
        # Check error type
        if error_type in ErrorHandler.ERROR_MESSAGES:
            return ErrorHandler.ERROR_MESSAGES[error_type]
        
        # Check partial matches
        for key, message in ErrorHandler.ERROR_MESSAGES.items():
            if key.lower() in error_str.lower():
                return message
        
        # Check category mappings
        error_lower = error_str.lower()
        for category, keywords in ErrorHandler.CATEGORY_MAPPINGS.items():
            for keyword in keywords:
                if keyword.lower() in error_lower or keyword.lower() in error_type.lower():
                    if category == 'connection':
                        return 'Kunne ikke oprette forbindelse til tjenesten. Prøv igen om et øjeblik.'
                    elif category == 'api_key':
                        return 'Videogenereringstjenesten er ikke konfigureret korrekt. Kontakt support.'
                    elif category == 'video_generation':
                        return 'Videogenerering mislykkedes. Prøv igen eller kontakt support hvis problemet fortsætter.'
                    elif category == 'file':
                        return 'Der opstod et problem med filhåndtering. Prøv igen.'
                    elif category == 'system':
                        return 'Systemet mangler en påkrævet komponent. Kontakt support.'
        
        # Generic fallback
        if fallback_message:
            return fallback_message
        
        return 'Der opstod en uventet fejl. Prøv igen, eller kontakt support hvis problemet fortsætter.'
    
    @staticmethod
    def sanitize_error_for_client(error: Exception, request_id: Optional[str] = None) -> Dict[str, str]:
        """
        Create sanitized error response for client with standardized format
        
        Args:
            error: Exception object
            request_id: Optional request ID for tracking
        
        Returns:
            Dictionary with user-friendly message, error code, and request ID
        """
        user_message = ErrorHandler.get_user_friendly_message(error)
        
        # Generate request ID if not provided
        if not request_id:
            request_id = str(uuid.uuid4())[:8]
        
        # Determine error code based on error type
        error_type = type(error).__name__
        if 'Connection' in error_type or 'Timeout' in error_type:
            error_code = 'CONNECTION_ERROR'
        elif 'Permission' in error_type or '401' in str(error) or '403' in str(error):
            error_code = 'AUTH_ERROR'
        elif 'FileNotFound' in error_type or 'No space' in str(error):
            error_code = 'FILE_ERROR'
        elif 'Import' in error_type or 'Module' in error_type:
            error_code = 'SYSTEM_ERROR'
        else:
            error_code = 'GENERATION_ERROR'
        
        # Log error with request ID
        logger.error(
            f"Error [{request_id}]: {error_type} - {str(error)}",
            extra={'request_id': request_id, 'error_type': error_type}
        )
        
        return {
            'success': False,
            'error': user_message,
            'error_code': error_code,
            'message': user_message,
            'request_id': request_id
        }
    
    @staticmethod
    def create_error_response(
        error: Exception,
        status_code: int = 500,
        request_id: Optional[str] = None
    ) -> tuple:
        """
        Create standardized error response with status code and error hash tracking
        
        Args:
            error: Exception object
            status_code: HTTP status code (default: 500)
            request_id: Optional request ID for tracking
        
        Returns:
            Tuple of (jsonify response, status_code)
        """
        from flask import jsonify, request
        
        # Track error with hash
        try:
            from backend.services.error_hash_tracking import error_hash_tracking
            
            endpoint = request.path if request else 'unknown'
            context = {
                'status_code': status_code,
                'request_id': request_id
            }
            
            error_hash_tracking.track_error(endpoint, error, context)
            error_hash_tracking.increment_request_count()
        except Exception:
            pass  # Silently fail if tracking unavailable
        
        error_data = ErrorHandler.sanitize_error_for_client(error, request_id)
        return jsonify(error_data), status_code

