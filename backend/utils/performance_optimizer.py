"""
Performance Optimization Utilities
Query optimization, connection pooling hints, and performance monitoring
"""
from functools import wraps
import time
from typing import Callable, Any
from backend.utils.monitoring import system_monitor


def track_performance(func: Callable) -> Callable:
    """
    Decorator to track endpoint performance
    
    Usage:
        @track_performance
        def my_endpoint():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            
            # Record performance metric
            endpoint_name = f"{func.__module__}.{func.__name__}"
            system_monitor.record_metric('endpoint_duration', duration, {
                'endpoint': endpoint_name,
                'status': 'success'
            })
            
            # Alert on slow endpoints (>2 seconds)
            if duration > 2.0:
                system_monitor.record_alert(
                    'warning',
                    f'Slow endpoint: {endpoint_name} took {duration:.2f}s',
                    'performance'
                )
            
            return result
        except Exception as e:
            duration = time.time() - start_time
            endpoint_name = f"{func.__module__}.{func.__name__}"
            system_monitor.record_metric('endpoint_duration', duration, {
                'endpoint': endpoint_name,
                'status': 'error'
            })
            raise
    
    return wrapper


def optimize_query(query_func: Callable) -> Callable:
    """
    Decorator to optimize database queries
    Adds query result caching hints
    """
    @wraps(query_func)
    def wrapper(*args, **kwargs):
        # Could add query plan analysis, caching hints, etc.
        return query_func(*args, **kwargs)
    return wrapper


def batch_operations(items: list, batch_size: int = 100):
    """
    Generator to process items in batches
    Useful for bulk database operations
    """
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]
