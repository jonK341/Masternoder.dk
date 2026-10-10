"""
Security logging utility
Logs security-related events for monitoring and auditing
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from flask import request, g


class SecurityLogger:
    """Security event logging"""
    
    logger = logging.getLogger('vidgenerator.security')
    
    @staticmethod
    def log_security_event(
        event_type: str,
        severity: str = 'info',
        details: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Log a security event
        
        Args:
            event_type: Type of security event (e.g., 'rate_limit_exceeded', 'csrf_failed', 'invalid_input')
            severity: Severity level ('info', 'warning', 'error', 'critical')
            details: Additional event details
            user_id: User ID if available
            ip_address: IP address if available
        """
        if details is None:
            details = {}
        
        # Get request context if available
        try:
            if not ip_address:
                ip_address = request.remote_addr if request else None
            
            if not user_id:
                user_id = getattr(g, 'user_id', None) or (request.session.get('user_id') if request and hasattr(request, 'session') else None)
            
            path = request.path if request else None
            method = request.method if request else None
        except RuntimeError:
            # No request context
            path = None
            method = None
        
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,
            'severity': severity,
            'ip_address': ip_address,
            'user_id': user_id,
            'path': path,
            'method': method,
            **details
        }
        
        # Log based on severity
        message = f"[SECURITY] {event_type} | IP: {ip_address} | Path: {path} | Method: {method}"
        if details:
            message += f" | Details: {details}"
        
        if severity == 'critical':
            SecurityLogger.logger.critical(message, extra=log_data)
        elif severity == 'error':
            SecurityLogger.logger.error(message, extra=log_data)
        elif severity == 'warning':
            SecurityLogger.logger.warning(message, extra=log_data)
        else:
            SecurityLogger.logger.info(message, extra=log_data)
    
    @staticmethod
    def log_rate_limit_exceeded(endpoint: str, ip_address: Optional[str] = None):
        """Log rate limit exceeded event"""
        SecurityLogger.log_security_event(
            'rate_limit_exceeded',
            severity='warning',
            details={'endpoint': endpoint},
            ip_address=ip_address
        )
    
    @staticmethod
    def log_csrf_failure(endpoint: Optional[str] = None):
        """Log CSRF token validation failure"""
        SecurityLogger.log_security_event(
            'csrf_failed',
            severity='warning',
            details={'endpoint': endpoint},
        )
    
    @staticmethod
    def log_invalid_input(endpoint: str, input_field: str, reason: str):
        """Log invalid input validation failure"""
        SecurityLogger.log_security_event(
            'invalid_input',
            severity='info',
            details={
                'endpoint': endpoint,
                'field': input_field,
                'reason': reason
            }
        )
    
    @staticmethod
    def log_suspicious_activity(activity_type: str, details: Optional[Dict[str, Any]] = None):
        """Log suspicious activity"""
        SecurityLogger.log_security_event(
            'suspicious_activity',
            severity='warning',
            details={'activity_type': activity_type, **(details or {})}
        )
    
    @staticmethod
    def log_authentication_failure(reason: str, user_id: Optional[str] = None):
        """Log authentication failure"""
        SecurityLogger.log_security_event(
            'authentication_failed',
            severity='warning',
            details={'reason': reason},
            user_id=user_id
        )
    
    @staticmethod
    def log_authorization_failure(endpoint: str, user_id: Optional[str] = None):
        """Log authorization failure"""
        SecurityLogger.log_security_event(
            'authorization_failed',
            severity='warning',
            details={'endpoint': endpoint},
            user_id=user_id
        )

