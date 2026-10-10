"""
Database query result caching utility
Provides in-memory caching for expensive database queries
"""
import time
import hashlib
import json
import logging
from typing import Any, Optional, Callable
from functools import wraps

logger = logging.getLogger('vidgenerator.cache')


class QueryCache:
    """Simple in-memory query result cache"""
    
    def __init__(self, default_ttl: int = 300):
        """
        Initialize query cache
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 5 minutes)
        """
        self.cache = {}
        self.default_ttl = default_ttl
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0
        }
    
    def _make_key(self, func_name: str, *args, **kwargs) -> str:
        """Generate cache key from function name and arguments"""
        # Serialize arguments to JSON for consistent hashing
        key_data = {
            'func': func_name,
            'args': args,
            'kwargs': kwargs
        }
        key_json = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_json.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired"""
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        entry = self.cache[key]
        if time.time() > entry['expires_at']:
            # Expired - remove it
            del self.cache[key]
            self.stats['evictions'] += 1
            self.stats['misses'] += 1
            return None
        
        self.stats['hits'] += 1
        return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Store value in cache with TTL"""
        ttl = ttl or self.default_ttl
        self.cache[key] = {
            'value': value,
            'expires_at': time.time() + ttl
        }
        self.stats['sets'] += 1
    
    def clear(self):
        """Clear all cache entries"""
        count = len(self.cache)
        self.cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")
    
    def get_stats(self) -> dict:
        """Get cache statistics"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self.cache),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'sets': self.stats['sets'],
            'evictions': self.stats['evictions'],
            'hit_rate': round(hit_rate, 2)
        }


# Global cache instance
_query_cache = QueryCache(default_ttl=300)  # 5 minutes default


def cached_query(ttl: int = 300, key_func: Optional[Callable] = None):
    """
    Decorator to cache database query results
    
    Usage:
        @cached_query(ttl=600)  # Cache for 10 minutes
        def get_statistics():
            return Documentary.query.filter_by(status='completed').count()
    
    Args:
        ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        key_func: Optional function to generate custom cache key
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _query_cache._make_key(func.__name__, *args, **kwargs)
            
            # Try to get from cache
            cached_value = _query_cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache HIT for {func.__name__}")
                return cached_value
            
            # Cache miss - execute function
            logger.debug(f"Cache MISS for {func.__name__}")
            result = func(*args, **kwargs)
            
            # Store in cache
            _query_cache.set(cache_key, result, ttl=ttl)
            
            return result
        
        wrapper.cache_clear = lambda: _query_cache.clear()
        wrapper.cache_stats = lambda: _query_cache.get_stats()
        return wrapper
    
    return decorator


def get_cache_stats() -> dict:
    """Get cache statistics"""
    return _query_cache.get_stats()


def clear_query_cache():
    """Clear all cached query results"""
    _query_cache.clear()

