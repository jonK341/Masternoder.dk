"""
Battle Arena Error Handlers
Comprehensive error handling for battle arena gear system
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging
import traceback
import sys

logger = logging.getLogger('battle_arena.errors')


class BattleArenaErrorHandler:
    """
    Comprehensive error handling system for battle arena gear operations
    """
    
    ERROR_HANDLERS = {}
    
    @staticmethod
    def register_handler(error_type: str, handler: Callable):
        """Register an error handler"""
        BattleArenaErrorHandler.ERROR_HANDLERS[error_type] = handler
    
    @staticmethod
    def handle_gear_not_found(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler 1: Gear not found errors"""
        logger.warning(f"Gear not found: {context.get('gear_id', 'unknown')}")
        return {
            'success': False,
            'error': 'gear_not_found',
            'message': 'Gear not found in definitions',
            'gear_id': context.get('gear_id'),
            'handler': 'gear_not_found_handler',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def handle_calculator_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler 2: Calculator integration errors"""
        logger.error(f"Calculator error: {str(error)}")
        return {
            'success': False,
            'error': 'calculator_error',
            'message': 'Failed to calculate gear stats using calculator',
            'user_id': context.get('user_id'),
            'gear_id': context.get('gear_id'),
            'handler': 'calculator_error_handler',
            'fallback_used': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def handle_division_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler 3: Division data extraction errors"""
        logger.warning(f"Division extraction error: {str(error)}")
        return {
            'success': False,
            'error': 'division_error',
            'message': 'Failed to extract user division data',
            'user_id': context.get('user_id'),
            'handler': 'division_error_handler',
            'defaults_used': True,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def handle_inventory_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler 4: Inventory management errors"""
        logger.error(f"Inventory error: {str(error)}")
        return {
            'success': False,
            'error': 'inventory_error',
            'message': 'Failed to manage gear inventory',
            'user_id': context.get('user_id'),
            'operation': context.get('operation'),
            'handler': 'inventory_error_handler',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def handle_json_storage_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler 5: JSON file storage errors"""
        logger.error(f"JSON storage error: {str(error)}")
        return {
            'success': False,
            'error': 'storage_error',
            'message': 'Failed to save/load gear data from JSON',
            'file': context.get('file'),
            'operation': context.get('operation'),
            'handler': 'json_storage_error_handler',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @staticmethod
    def handle_validation_error(error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Handler 6: Input validation errors"""
        logger.warning(f"Validation error: {str(error)}")
        return {
            'success': False,
            'error': 'validation_error',
            'message': 'Invalid input parameters',
            'field': context.get('field'),
            'value': context.get('value'),
            'handler': 'validation_error_handler',
            'timestamp': datetime.utcnow().isoformat()
        }
    
    @classmethod
    def handle_error(cls, error: Exception, error_type: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Main error handling method that routes to appropriate handler
        """
        if context is None:
            context = {}
        
        context['error_message'] = str(error)
        context['error_type'] = type(error).__name__
        context['traceback'] = traceback.format_exc()
        
        # Route to specific handler if registered
        if error_type in cls.ERROR_HANDLERS:
            handler = cls.ERROR_HANDLERS[error_type]
            return handler(error, context)
        
        # Route to default handlers based on error type
        error_name = type(error).__name__.lower()
        
        if 'notfound' in error_name or 'not found' in str(error).lower():
            return cls.handle_gear_not_found(error, context)
        elif 'calculator' in error_name or 'calculate' in str(error).lower():
            return cls.handle_calculator_error(error, context)
        elif 'division' in error_name or 'profile' in str(error).lower():
            return cls.handle_division_error(error, context)
        elif 'inventory' in error_name or 'inventory' in str(error).lower():
            return cls.handle_inventory_error(error, context)
        elif 'json' in error_name or 'file' in error_name or 'io' in error_name:
            return cls.handle_json_storage_error(error, context)
        elif 'value' in error_name or 'validation' in error_name or 'type' in error_name:
            return cls.handle_validation_error(error, context)
        else:
            # Generic handler
            logger.error(f"Unhandled error: {str(error)}")
            return {
                'success': False,
                'error': 'unknown_error',
                'message': 'An unexpected error occurred',
                'error_type': type(error).__name__,
                'handler': 'generic_error_handler',
                'timestamp': datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def safe_execute(func: Callable, error_type: str, context: Dict[str, Any] = None, fallback: Callable = None):
        """
        Safely execute a function with error handling
        """
        try:
            return func()
        except Exception as e:
            error_response = BattleArenaErrorHandler.handle_error(e, error_type, context)
            
            if fallback:
                try:
                    return fallback(error_response)
                except:
                    pass
            
            return error_response


# Register default handlers
BattleArenaErrorHandler.register_handler('gear_not_found', BattleArenaErrorHandler.handle_gear_not_found)
BattleArenaErrorHandler.register_handler('calculator_error', BattleArenaErrorHandler.handle_calculator_error)
BattleArenaErrorHandler.register_handler('division_error', BattleArenaErrorHandler.handle_division_error)
BattleArenaErrorHandler.register_handler('inventory_error', BattleArenaErrorHandler.handle_inventory_error)
BattleArenaErrorHandler.register_handler('storage_error', BattleArenaErrorHandler.handle_json_storage_error)
BattleArenaErrorHandler.register_handler('validation_error', BattleArenaErrorHandler.handle_validation_error)

