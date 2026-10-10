"""
Leaderboard Cache System
Optimized caching for leaderboard queries
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import hashlib
import json

try:
    from backend.services.cache_system import cache_system
    from src.utils.query_cache import _query_cache
except ImportError:
    cache_system = None
    _query_cache = None


class LeaderboardCache:
    """Specialized caching for leaderboard data"""
    
    def __init__(self):
        self.default_ttl = 60  # 1 minute for leaderboards (frequent updates)
        self.stats_ttl = 300  # 5 minutes for statistics
        self.user_rank_ttl = 30  # 30 seconds for user rank
    
    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate cache key"""
        key_data = {
            'prefix': prefix,
            'args': args,
            'kwargs': sorted(kwargs.items()) if kwargs else []
        }
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        return f"leaderboard:{hashlib.md5(key_str.encode()).hexdigest()}"
    
    def cache_leaderboard(self, system_id: str, period: str, limit: int, 
                         leaderboard_data: List[Dict[str, Any]], ttl: Optional[int] = None) -> bool:
        """Cache leaderboard data - accepts both 'period' and 'timeframe' for compatibility"""
        """Cache leaderboard data"""
        key = self._make_key('board', system_id, period, limit)
        ttl = ttl or self.default_ttl
        
        if cache_system:
            return cache_system.set(key, leaderboard_data, timeout=ttl)
        elif _query_cache:
            _query_cache.set(key, leaderboard_data, ttl=ttl)
            return True
        return False
    
    def get_cached_leaderboard(self, system_id: str, period: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached leaderboard data"""
        key = self._make_key('board', system_id, period, limit)
        
        if cache_system:
            return cache_system.get(key)
        elif _query_cache:
            return _query_cache.get(key)
        return None
    
    def cache_user_rank(self, user_id: str, system_id: str, rank_data: Dict[str, Any], 
                       ttl: Optional[int] = None) -> bool:
        """Cache user rank data"""
        key = self._make_key('rank', user_id, system_id)
        ttl = ttl or self.user_rank_ttl
        
        if cache_system:
            return cache_system.set(key, rank_data, timeout=ttl)
        elif _query_cache:
            _query_cache.set(key, rank_data, ttl=ttl)
            return True
        return False
    
    def get_cached_user_rank(self, user_id: str, system_id: str) -> Optional[Dict[str, Any]]:
        """Get cached user rank"""
        key = self._make_key('rank', user_id, system_id)
        
        if cache_system:
            return cache_system.get(key)
        elif _query_cache:
            return _query_cache.get(key)
        return None
    
    def cache_statistics(self, system_id: str, stats_data: Dict[str, Any], 
                        ttl: Optional[int] = None) -> bool:
        """Cache leaderboard statistics"""
        key = self._make_key('stats', system_id)
        ttl = ttl or self.stats_ttl
        
        if cache_system:
            return cache_system.set(key, stats_data, timeout=ttl)
        elif _query_cache:
            _query_cache.set(key, stats_data, ttl=ttl)
            return True
        return False
    
    def get_cached_statistics(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get cached statistics"""
        key = self._make_key('stats', system_id)
        
        if cache_system:
            return cache_system.get(key)
        elif _query_cache:
            return _query_cache.get(key)
        return None
    
    def invalidate_leaderboard(self, system_id: Optional[str] = None):
        """Invalidate leaderboard cache"""
        # In a real implementation, would use pattern matching
        # For now, clear all leaderboard cache
        if cache_system:
            # Would need pattern-based deletion
            pass
        elif _query_cache:
            # Clear all cache (simple implementation)
            _query_cache.clear()
    
    def invalidate_user_cache(self, user_id: str):
        """Invalidate all cache for a user"""
        if cache_system:
            cache_system.invalidate_user_cache(user_id)
        # Also invalidate leaderboard cache as user rank changed
        self.invalidate_leaderboard()


# Global instance
leaderboard_cache = LeaderboardCache()
