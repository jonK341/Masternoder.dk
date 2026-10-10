"""
Retry handler utility for operations that may fail transiently
Provides exponential backoff and configurable retry policies
"""
import time
import logging
from typing import Callable, Optional, Type, Tuple, Any
from functools import wraps

logger = logging.getLogger('vidgenerator.retry')


class RetryHandler:
    """Handles retries with exponential backoff"""
    
    @staticmethod
    def retry(
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
        on_retry: Optional[Callable[[int, Exception], None]] = None
    ):
        """
        Decorator to retry a function with exponential backoff
        
        Args:
            max_attempts: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds (default: 1.0)
            max_delay: Maximum delay in seconds (default: 60.0)
            exponential_base: Base for exponential backoff (default: 2.0)
            retryable_exceptions: Tuple of exception types to retry (default: all)
            on_retry: Optional callback function(attempt_number, exception)
        
        Usage:
            @RetryHandler.retry(max_attempts=3, base_delay=1.0)
            def my_function():
                # Code that may fail
                pass
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                last_exception = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        return func(*args, **kwargs)
                    except retryable_exceptions as e:
                        last_exception = e
                        
                        # Check if this is the last attempt
                        if attempt >= max_attempts:
                            logger.error(
                                f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                            )
                            raise
                        
                        # Calculate delay with exponential backoff
                        delay = min(
                            base_delay * (exponential_base ** (attempt - 1)),
                            max_delay
                        )
                        
                        logger.warning(
                            f"Function {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        
                        # Call retry callback if provided
                        if on_retry:
                            try:
                                on_retry(attempt, e)
                            except Exception as callback_err:
                                logger.error(f"Error in retry callback: {callback_err}")
                        
                        # Wait before retrying
                        time.sleep(delay)
                
                # Should never reach here, but just in case
                if last_exception:
                    raise last_exception
                    
            return wrapper
        return decorator


def retry_on_failure(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Convenience function for retrying operations
    
    Usage:
        result = retry_on_failure(max_attempts=3)(
            lambda: some_operation()
        )
    """
    return RetryHandler.retry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        retryable_exceptions=retryable_exceptions
    )

