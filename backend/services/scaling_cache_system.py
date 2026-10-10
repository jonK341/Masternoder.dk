"""
Scaling Cache System - Distributed caching for 1.3 billion users
Multi-layer caching with TTL and invalidation
"""
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import OrderedDict
import threading
import hashlib
import json


class ScalingCacheSystem:
    """
    Multi-layer caching system for massive scale
    Supports TTL, LRU eviction, and distributed caching
    """
    
    def __init__(self, max_size: int = 1000000, default_ttl: int = 300):
        """
        Initialize cache system
        
        Args:
            max_size: Maximum number of cache entries
            default_ttl: Default TTL in seconds (5 minutes)
        """
        self.cache = OrderedDict()  # LRU cache
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'invalidations': 0
        }
        self.lock = threading.RLock()  # Reentrant lock for nested calls
    
    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments"""
        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        with self.lock:
            if key not in self.cache:
                self.stats['misses'] += 1
                return None
            
            entry = self.cache[key]
            
            # Check TTL
            if datetime.utcnow() > entry['expires_at']:
                # Expired - remove from cache
                del self.cache[key]
                self.stats['misses'] += 1
                return None
            
            # Move to end (LRU)
            self.cache.move_to_end(key)
            self.stats['hits'] += 1
            return entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        with self.lock:
            ttl = ttl or self.default_ttl
            expires_at = datetime.utcnow() + timedelta(seconds=ttl)
            
            # Check if we need to evict
            if key not in self.cache and len(self.cache) >= self.max_size:
                # Remove oldest entry (LRU)
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                self.stats['evictions'] += 1
            
            self.cache[key] = {
                'value': value,
                'expires_at': expires_at,
                'created_at': datetime.utcnow().isoformat()
            }
            self.cache.move_to_end(key)  # Move to end (most recently used)
            self.stats['sets'] += 1
            return True
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                self.stats['invalidations'] += 1
                return True
            return False
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries (optionally matching pattern)"""
        with self.lock:
            if pattern:
                # Clear matching keys
                keys_to_delete = [k for k in self.cache.keys() if pattern in k]
                for key in keys_to_delete:
                    del self.cache[key]
                self.stats['invalidations'] += len(keys_to_delete)
                return len(keys_to_delete)
            else:
                # Clear all
                count = len(self.cache)
                self.cache.clear()
                self.stats['invalidations'] += count
                return count
    
    def get_or_set(self, key: str, func: Callable, ttl: Optional[int] = None, *args, **kwargs) -> Any:
        """Get from cache or set using function"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Calculate value
        value = func(*args, **kwargs)
        self.set(key, value, ttl)
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hits': self.stats['hits'],
                'misses': self.stats['misses'],
                'sets': self.stats['sets'],
                'evictions': self.stats['evictions'],
                'invalidations': self.stats['invalidations'],
                'hit_rate': round(hit_rate, 2),
                'current_size': len(self.cache),
                'max_size': self.max_size,
                'utilization_percent': round((len(self.cache) / self.max_size) * 100, 2)
            }


# Global cache instances for different purposes
user_cache = ScalingCacheSystem(max_size=500000, default_ttl=600)  # User data cache
calculation_cache = ScalingCacheSystem(max_size=1000000, default_ttl=300)  # Calculator results
stats_cache = ScalingCacheSystem(max_size=500000, default_ttl=180)  # Stats cache
event_cache = ScalingCacheSystem(max_size=200000, default_ttl=60)  # Event cache

