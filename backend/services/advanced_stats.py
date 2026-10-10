"""
Advanced Stats Dashboard
Detailed analytics, performance graphs, comparison tools, trend analysis
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class AdvancedStats:
    """Advanced statistics and analytics"""
    
    def __init__(self):
        """Initialize advanced stats"""
        self.user_stats_history = defaultdict(list)  # {user_id: [stat_snapshots]}
        self.global_stats = {}
    
    def record_stat_snapshot(self, user_id: str, stats: Dict[str, Any]):
        """Record a stat snapshot"""
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'stats': stats
        }
        self.user_stats_history[user_id].append(snapshot)
        
        # Keep only last 100 snapshots per user
        if len(self.user_stats_history[user_id]) > 100:
            self.user_stats_history[user_id] = self.user_stats_history[user_id][-100:]
    
    def get_user_trends(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get user trends over time"""
        history = self.user_stats_history.get(user_id, [])
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_history = [
            h for h in history 
            if datetime.fromisoformat(h['timestamp']) >= cutoff
        ]
        
        if not recent_history:
            return {
                'trends': {},
                'growth': {},
                'period': days
            }
        
        # Calculate trends
        first_stats = recent_history[0]['stats']
        last_stats = recent_history[-1]['stats']
        
        trends = {}
        growth = {}
        
        for key in ['level', 'total_xp', 'wins', 'total_battles']:
            if key in first_stats and key in last_stats:
                first_val = first_stats.get(key, 0)
                last_val = last_stats.get(key, 0)
                growth[key] = last_val - first_val
                if first_val > 0:
                    trends[key] = ((last_val - first_val) / first_val) * 100
                else:
                    trends[key] = 100 if last_val > 0 else 0
        
        return {
            'trends': trends,
            'growth': growth,
            'period': days,
            'data_points': len(recent_history)
        }
    
    def get_performance_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get performance metrics"""
        history = self.user_stats_history.get(user_id, [])
        
        if not history:
            return {
                'metrics': {},
                'averages': {},
                'totals': {}
            }
        
        # Calculate averages and totals
        all_stats = [h['stats'] for h in history]
        
        metrics = {
            'total_snapshots': len(all_stats),
            'first_recorded': history[0]['timestamp'],
            'last_recorded': history[-1]['timestamp']
        }
        
        # Calculate averages
        averages = {}
        totals = {}
        
        numeric_keys = ['level', 'total_xp', 'wins', 'losses', 'total_battles']
        for key in numeric_keys:
            values = [s.get(key, 0) for s in all_stats if key in s]
            if values:
                averages[key] = sum(values) / len(values)
                totals[key] = max(values) if values else 0
        
        return {
            'metrics': metrics,
            'averages': averages,
            'totals': totals
        }
    
    def compare_users(self, user1_id: str, user2_id: str) -> Dict[str, Any]:
        """Compare two users"""
        user1_history = self.user_stats_history.get(user1_id, [])
        user2_history = self.user_stats_history.get(user2_id, [])
        
        user1_latest = user1_history[-1]['stats'] if user1_history else {}
        user2_latest = user2_history[-1]['stats'] if user2_history else {}
        
        comparison = {}
        
        for key in ['level', 'total_xp', 'wins', 'rating']:
            val1 = user1_latest.get(key, 0)
            val2 = user2_latest.get(key, 0)
            
            comparison[key] = {
                'user1': val1,
                'user2': val2,
                'difference': val1 - val2,
                'winner': 'user1' if val1 > val2 else ('user2' if val2 > val1 else 'tie')
            }
        
        return {
            'user1_id': user1_id,
            'user2_id': user2_id,
            'comparison': comparison
        }
    
    def get_category_breakdown(self, user_id: str) -> Dict[str, Any]:
        """Get breakdown by category"""
        history = self.user_stats_history.get(user_id, [])
        
        if not history:
            return {
                'categories': {},
                'distribution': {}
            }
        
        latest = history[-1]['stats']
        
        # Extract category stats
        categories = {}
        if 'category_videos' in latest:
            categories = latest['category_videos']
        
        total = sum(categories.values()) if categories else 1
        
        distribution = {
            cat: (count / total * 100) if total > 0 else 0
            for cat, count in categories.items()
        }
        
        return {
            'categories': categories,
            'distribution': distribution
        }
    
    def get_time_series_data(self, user_id: str, metric: str, days: int = 7) -> List[Dict]:
        """Get time series data for a metric"""
        history = self.user_stats_history.get(user_id, [])
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        recent_history = [
            h for h in history 
            if datetime.fromisoformat(h['timestamp']) >= cutoff
        ]
        
        time_series = []
        for snapshot in recent_history:
            value = snapshot['stats'].get(metric, 0)
            time_series.append({
                'timestamp': snapshot['timestamp'],
                'value': value
            })
        
        return time_series
    
    def get_global_stats(self) -> Dict[str, Any]:
        """Get global statistics"""
        all_users = list(self.user_stats_history.keys())
        
        if not all_users:
            return {
                'total_users': 0,
                'average_level': 0,
                'total_xp': 0
            }
        
        # Aggregate stats
        total_level = 0
        total_xp = 0
        active_users = 0
        
        for user_id in all_users:
            history = self.user_stats_history.get(user_id, [])
            if history:
                latest = history[-1]['stats']
                total_level += latest.get('level', 0)
                total_xp += latest.get('total_xp', 0)
                active_users += 1
        
        return {
            'total_users': len(all_users),
            'active_users': active_users,
            'average_level': total_level / active_users if active_users > 0 else 0,
            'total_xp': total_xp,
            'average_xp': total_xp / active_users if active_users > 0 else 0
        }


# Global instance
advanced_stats = AdvancedStats()

