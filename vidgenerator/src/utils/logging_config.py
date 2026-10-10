"""
Comprehensive logging configuration for the Flask application
Provides structured logging with file rotation, error tracking, and monitoring
"""
import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Structured log formatter with timestamps, levels, and context"""
    
    def __init__(self, include_context: bool = True):
        super().__init__()
        self.include_context = include_context
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with structured information"""
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Base log line
        log_parts = [
            f"[{timestamp}]",
            f"[{record.levelname}]",
            f"[{record.name}]",
            record.getMessage()
        ]
        
        # Add context if available
        if self.include_context and hasattr(record, 'context'):
            context_str = ' '.join([f"{k}={v}" for k, v in record.context.items()])
            log_parts.append(f"| {context_str}")
        
        # Add exception info if present
        if record.exc_info:
            log_parts.append(f"\n{self.formatException(record.exc_info)}")
        
        return ' '.join(log_parts)


class LoggingConfig:
    """Centralized logging configuration"""
    
    # Log directory
    LOG_DIR = os.getenv('LOG_DIR', '/var/www/html/vidgenerator/logs')
    
    # Log file names
    APP_LOG = 'app.log'
    ERROR_LOG = 'errors.log'
    ACCESS_LOG = 'access.log'
    PERFORMANCE_LOG = 'performance.log'
    
    # Log file sizes (10MB)
    MAX_BYTES = 10 * 1024 * 1024
    
    # Number of backup files to keep
    BACKUP_COUNT = 5
    
    _configured = False
    
    @classmethod
    def configure_logging(cls, app_name: str = 'vidgenerator', log_level: str = None) -> None:
        """
        Configure comprehensive logging for the application
        
        Args:
            app_name: Application name for logger
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        if cls._configured:
            return
        
        # Determine log level
        if log_level is None:
            log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        
        level = getattr(logging, log_level, logging.INFO)
        
        # Create log directory
        log_dir = Path(cls.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(level)
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = StructuredFormatter(include_context=False)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # Application log handler (rotating file)
        app_log_file = log_dir / cls.APP_LOG
        app_handler = logging.handlers.RotatingFileHandler(
            str(app_log_file),
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        app_handler.setLevel(logging.DEBUG)
        app_formatter = StructuredFormatter(include_context=True)
        app_handler.setFormatter(app_formatter)
        root_logger.addHandler(app_handler)
        
        # Error log handler (separate file for errors and above)
        error_log_file = log_dir / cls.ERROR_LOG
        error_handler = logging.handlers.RotatingFileHandler(
            str(error_log_file),
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_formatter = StructuredFormatter(include_context=True)
        error_handler.setFormatter(error_formatter)
        root_logger.addHandler(error_handler)
        
        # Performance log handler (separate file for performance metrics)
        perf_log_file = log_dir / cls.PERFORMANCE_LOG
        perf_handler = logging.handlers.RotatingFileHandler(
            str(perf_log_file),
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        perf_handler.setLevel(logging.INFO)
        perf_formatter = logging.Formatter(
            '[%(asctime)s] [PERFORMANCE] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        perf_handler.setFormatter(perf_formatter)
        
        # Create performance logger (separate from main logger)
        perf_logger = logging.getLogger('performance')
        perf_logger.addHandler(perf_handler)
        perf_logger.setLevel(logging.INFO)
        perf_logger.propagate = False  # Don't propagate to root logger
        
        # Access log handler (for HTTP requests)
        access_log_file = log_dir / cls.ACCESS_LOG
        access_handler = logging.handlers.RotatingFileHandler(
            str(access_log_file),
            maxBytes=cls.MAX_BYTES,
            backupCount=cls.BACKUP_COUNT,
            encoding='utf-8'
        )
        access_handler.setLevel(logging.INFO)
        access_formatter = logging.Formatter(
            '[%(asctime)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        access_handler.setFormatter(access_formatter)
        
        # Create access logger (separate from main logger)
        access_logger = logging.getLogger('access')
        access_logger.addHandler(access_handler)
        access_logger.setLevel(logging.INFO)
        access_logger.propagate = False  # Don't propagate to root logger
        
        # Configure third-party loggers
        logging.getLogger('werkzeug').setLevel(logging.WARNING)  # Reduce Flask request logs
        logging.getLogger('urllib3').setLevel(logging.WARNING)  # Reduce HTTP client logs
        logging.getLogger('requests').setLevel(logging.WARNING)  # Reduce requests logs
        
        cls._configured = True
        
        # Log configuration completion
        logger = logging.getLogger(app_name)
        logger.info(f"Logging configured: level={log_level}, log_dir={log_dir}")
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """Get a logger instance with the given name"""
        return logging.getLogger(name)
    
    @classmethod
    def get_performance_logger(cls) -> logging.Logger:
        """Get the performance logger"""
        return logging.getLogger('performance')
    
    @classmethod
    def get_access_logger(cls) -> logging.Logger:
        """Get the access logger"""
        return logging.getLogger('access')


class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    @staticmethod
    def log_request_time(endpoint: str, method: str, duration_ms: float, status_code: int = None):
        """Log request performance metrics"""
        perf_logger = LoggingConfig.get_performance_logger()
        status_str = f"status={status_code}" if status_code else ""
        perf_logger.info(f"REQUEST | endpoint={endpoint} | method={method} | duration={duration_ms:.2f}ms {status_str}")
    
    @staticmethod
    def log_api_call(api_name: str, duration_ms: float, success: bool = True, error: str = None):
        """Log external API call performance"""
        perf_logger = LoggingConfig.get_performance_logger()
        status = "SUCCESS" if success else "FAILED"
        error_str = f" | error={error}" if error else ""
        perf_logger.info(f"API | name={api_name} | duration={duration_ms:.2f}ms | status={status}{error_str}")
    
    @staticmethod
    def log_database_query(query_type: str, duration_ms: float, rows_affected: int = None):
        """Log database query performance"""
        perf_logger = LoggingConfig.get_performance_logger()
        rows_str = f" | rows={rows_affected}" if rows_affected is not None else ""
        perf_logger.info(f"DB | query={query_type} | duration={duration_ms:.2f}ms{rows_str}")
    
    @staticmethod
    def log_video_generation(doc_id: str, stage: str, duration_ms: float, success: bool = True):
        """Log video generation performance"""
        perf_logger = LoggingConfig.get_performance_logger()
        status = "SUCCESS" if success else "FAILED"
        perf_logger.info(f"VIDEO_GEN | doc_id={doc_id} | stage={stage} | duration={duration_ms:.2f}ms | status={status}")


class ErrorTracker:
    """Track and log errors with context"""
    
    @staticmethod
    def log_error(
        logger: logging.Logger,
        error: Exception,
        context: dict = None,
        user_id: str = None,
        request_path: str = None
    ):
        """
        Log error with full context
        
        Args:
            logger: Logger instance
            error: Exception object
            context: Additional context dictionary
            user_id: User ID if available
            request_path: Request path if available
        """
        error_context = context or {}
        if user_id:
            error_context['user_id'] = user_id
        if request_path:
            error_context['request_path'] = request_path
        
        # Create log record with context
        log_record = logger.makeRecord(
            logger.name,
            logging.ERROR,
            error.__class__.__name__,
            0,
            str(error),
            (error,),
            None
        )
        log_record.context = error_context
        logger.handle(log_record)
        
        # Also log traceback if available
        import traceback
        logger.error(f"Error traceback:\n{traceback.format_exc()}", extra={'context': error_context})


def setup_flask_logging(app):
    """
    Setup Flask-specific logging with request/response logging
    
    Args:
        app: Flask application instance
    """
    import time
    from flask import request, g
    
    access_logger = LoggingConfig.get_access_logger()
    
    @app.before_request
    def log_request_start():
        """Log request start and record start time"""
        g.start_time = time.time()
    
    @app.after_request
    def log_request_end(response):
        """Log request completion with metrics"""
        # Calculate duration
        duration_seconds = time.time() - g.start_time
        duration_ms = duration_seconds * 1000  # Convert to milliseconds
        
        # Log access
        access_logger.info(
            f"{request.method} {request.path} | "
            f"status={response.status_code} | "
            f"duration={duration_ms:.2f}ms | "
            f"ip={request.remote_addr} | "
            f"user_agent={request.headers.get('User-Agent', 'unknown')[:50]}"
        )
        
        # Log performance
        PerformanceMonitor.log_request_time(
            request.path,
            request.method,
            duration_ms,
            response.status_code
        )
        
        # Track metrics for system metrics endpoint
        try:
            from src.utils.system_metrics import get_system_metrics
            metrics = get_system_metrics()
            metrics.record_request(
                endpoint=request.path,
                duration=duration_seconds,
                status_code=response.status_code
            )
        except Exception:
            # Metrics tracking is optional, don't fail if it errors
            pass
        
        return response
    
    # Log unhandled exceptions
    @app.errorhandler(500)
    def log_internal_error(error):
        """Log 500 errors"""
        logger = LoggingConfig.get_logger('flask.app')
        ErrorTracker.log_error(
            logger,
            error,
            context={
                'request_path': request.path,
                'request_method': request.method,
                'user_agent': request.headers.get('User-Agent', 'unknown')
            }
        )
        return error
    
    # Log 404 errors (optional - can be verbose)
    @app.errorhandler(404)
    def log_not_found(error):
        """Log 404 errors (at DEBUG level to reduce noise)"""
        logger = LoggingConfig.get_logger('flask.app')
        logger.debug(f"404 Not Found: {request.path} | method={request.method} | ip={request.remote_addr}")
        return error
    
    # Log all exceptions (including unhandled)
    @app.errorhandler(Exception)
    def log_all_exceptions(error):
        """Log all unhandled exceptions"""
        logger = LoggingConfig.get_logger('flask.app')
        ErrorTracker.log_error(
            logger,
            error,
            context={
                'request_path': request.path,
                'request_method': request.method,
                'user_agent': request.headers.get('User-Agent', 'unknown'),
                'remote_addr': request.remote_addr
            }
        )
        # Re-raise to let Flask handle it normally
        raise error

