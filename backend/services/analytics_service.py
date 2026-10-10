"""
Analytics Service
Comprehensive analytics data collection and aggregation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

try:
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.quick_battle_system import quick_battle
    from backend.services.ip_mac_user_manager import ip_mac_user_manager
except ImportError:
    unified_point_counter = None
    quick_battle = None
    ip_mac_user_manager = None

# Module name starts with a digit, so import it via importlib; fall back gracefully.
try:
    import importlib
    leaderboard_178_systems = getattr(
        importlib.import_module('backend.services.178_systems_leaderboard'),
        'leaderboard_178_systems',
        None,
    )
except Exception:
    leaderboard_178_systems = None


class AnalyticsService:
    """Service for collecting and aggregating analytics data"""
    
    def __init__(self):
        self.metrics_cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_system_overview(self) -> Dict[str, Any]:
        """
        Get overall system overview statistics
        
        Returns:
            System overview with key metrics
        """
        overview = {
            'timestamp': datetime.utcnow().isoformat(),
            'users': self._get_user_metrics(),
            'battles': self._get_battle_metrics(),
            'points': self._get_points_metrics(),
            'activity': self._get_activity_metrics(),
            'performance': self._get_performance_metrics()
        }
        
        return overview
    
    def _get_user_metrics(self) -> Dict[str, Any]:
        """Get user-related metrics"""
        metrics = {
            'total_users': 0,
            'active_today': 0,
            'active_this_week': 0,
            'active_this_month': 0,
            'new_users_today': 0,
            'new_users_this_week': 0,
            'new_users_this_month': 0
        }
        
        if ip_mac_user_manager:
            try:
                all_users = ip_mac_user_manager.get_all_users()
                metrics['total_users'] = len(all_users)
                
                # Calculate active users
                now = datetime.utcnow()
                today = now.date()
                week_ago = (now - timedelta(days=7)).date()
                month_ago = (now - timedelta(days=30)).date()
                
                for user_id, user_data in all_users.items():
                    last_seen = user_data.get('last_seen')
                    created_at = user_data.get('created_at')
                    
                    if last_seen:
                        last_seen_date = datetime.fromisoformat(last_seen).date()
                        if last_seen_date == today:
                            metrics['active_today'] += 1
                        if last_seen_date >= week_ago:
                            metrics['active_this_week'] += 1
                        if last_seen_date >= month_ago:
                            metrics['active_this_month'] += 1
                    
                    if created_at:
                        created_date = datetime.fromisoformat(created_at).date()
                        if created_date == today:
                            metrics['new_users_today'] += 1
                        if created_date >= week_ago:
                            metrics['new_users_this_week'] += 1
                        if created_date >= month_ago:
                            metrics['new_users_this_month'] += 1
            except:
                pass
        
        return metrics
    
    def _get_battle_metrics(self) -> Dict[str, Any]:
        """Get battle-related metrics"""
        metrics = {
            'total_battles': 0,
            'active_battles': 0,
            'completed_today': 0,
            'avg_duration': 0,
            'total_spectators': 0,
            'matchmaking_queue_size': 0
        }
        
        if quick_battle:
            try:
                # Get battle counters
                all_counters = quick_battle.battle_counters
                total = sum(c.get('total_battles', 0) for c in all_counters.values())
                active = sum(c.get('active_battles', 0) for c in all_counters.values())
                
                metrics['total_battles'] = total
                metrics['active_battles'] = active
                
                # Matchmaking queue
                metrics['matchmaking_queue_size'] = len(quick_battle.matchmaking_queue)
                
                # Spectators
                try:
                    from backend.services.spectator_system import spectator_system
                    total_spectators = sum(len(s) for s in spectator_system.spectators.values())
                    metrics['total_spectators'] = total_spectators
                except:
                    pass
            except:
                pass
        
        return metrics
    
    def _get_points_metrics(self) -> Dict[str, Any]:
        """Get points-related metrics"""
        metrics = {
            'total_points_awarded': 0,
            'points_today': 0,
            'points_this_week': 0,
            'points_this_month': 0,
            'avg_points_per_user': 0,
            'top_point_category': None
        }
        
        if unified_point_counter:
            try:
                # This would require tracking point awards over time
                # For now, return basic structure
                pass
            except:
                pass
        
        return metrics
    
    def _get_activity_metrics(self) -> Dict[str, Any]:
        """Get activity-related metrics"""
        metrics = {
            'api_requests_today': 0,
            'api_requests_this_week': 0,
            'avg_response_time': 0,
            'error_rate': 0,
            'cache_hit_rate': 0
        }
        
        # Would integrate with request tracking
        return metrics
    
    def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance-related metrics"""
        metrics = {
            'avg_response_time': 0,
            'p95_response_time': 0,
            'p99_response_time': 0,
            'error_rate': 0,
            'cache_hit_rate': 0,
            'database_queries': 0
        }
        
        # Would integrate with performance monitoring
        return metrics
    
    def get_user_behavior_analytics(self, timeframe: str = 'week') -> Dict[str, Any]:
        """
        Get user behavior analytics
        
        Args:
            timeframe: 'day', 'week', 'month'
            
        Returns:
            User behavior data
        """
        behavior = {
            'timeframe': timeframe,
            'active_users': 0,
            'engagement_rate': 0,
            'retention_rate': 0,
            'avg_session_duration': 0,
            'peak_hours': [],
            'activity_breakdown': {}
        }
        
        if ip_mac_user_manager:
            try:
                all_users = ip_mac_user_manager.get_all_users()
                behavior['active_users'] = len(all_users)
            except:
                pass
        
        return behavior
    
    def get_revenue_analytics(self) -> Dict[str, Any]:
        """Get revenue analytics (if monetization enabled)"""
        return {
            'total_revenue': 0,
            'revenue_today': 0,
            'revenue_this_week': 0,
            'revenue_this_month': 0,
            'avg_revenue_per_user': 0,
            'top_revenue_sources': []
        }
    
    def get_leaderboard_analytics(self) -> Dict[str, Any]:
        """Get leaderboard analytics"""
        analytics = {
            'total_leaderboards': 0,
            'total_rankings': 0,
            'most_active_system': None,
            'top_users_count': 0,
            'rank_distribution': {}
        }
        
        if leaderboard_178_systems:
            try:
                # Get leaderboard statistics
                analytics['total_leaderboards'] = 178  # 178 systems
            except:
                pass
        
        return analytics
    
    def export_analytics(self, format: str = 'json') -> Dict[str, Any]:
        """
        Export analytics data
        
        Args:
            format: 'json', 'csv'
            
        Returns:
            Exported data
        """
        data = {
            'system_overview': self.get_system_overview(),
            'user_behavior': self.get_user_behavior_analytics(),
            'battle_metrics': self._get_battle_metrics(),
            'points_metrics': self._get_points_metrics(),
            'leaderboard_analytics': self.get_leaderboard_analytics(),
            'exported_at': datetime.utcnow().isoformat()
        }
        
        if format == 'csv':
            # Convert to CSV format
            csv_data = self._convert_to_csv(data)
            return {
                'success': True,
                'format': 'csv',
                'data': csv_data
            }
        
        return {
            'success': True,
            'format': 'json',
            'data': data
        }
    
    def _convert_to_csv(self, data: Dict[str, Any]) -> str:
        """Convert analytics data to CSV format"""
        # Simple CSV conversion
        lines = []
        lines.append('Metric,Value')
        
        overview = data.get('system_overview', {})
        users = overview.get('users', {})
        battles = overview.get('battles', {})
        
        for key, value in users.items():
            lines.append(f'users_{key},{value}')
        
        for key, value in battles.items():
            lines.append(f'battles_{key},{value}')
        
        return '\n'.join(lines)


# Global instance
analytics_service = AnalyticsService()
