"""
Point Analytics Dashboard
Provides comprehensive analytics for point systems
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

class PointAnalyticsDashboard:
    """Provides analytics for point systems"""
    
    def __init__(self):
        try:
            from backend.services.point_history_tracking import point_history_tracking
            self.history_tracker = point_history_tracking
        except ImportError:
            self.history_tracker = None
        
        try:
            from backend.services.unified_point_system_json_storage import unified_point_system
            self.point_system = unified_point_system
        except ImportError:
            self.point_system = None
    
    def get_comprehensive_analytics(self, user_id: str, 
                                   days: int = 30) -> Dict[str, Any]:
        """Get comprehensive point analytics"""
        analytics = {
            'user_id': user_id,
            'period_days': days,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Get current points
        if self.point_system:
            try:
                current_points = self.point_system.get_all_points(user_id)
                analytics['current_points'] = current_points
            except:
                analytics['current_points'] = {}
        else:
            analytics['current_points'] = {}
        
        # Get history statistics
        if self.history_tracker:
            try:
                stats = self.history_tracker.get_point_statistics(user_id, days=days)
                analytics['history_stats'] = stats
            except:
                analytics['history_stats'] = {}
        else:
            analytics['history_stats'] = {}
        
        # Calculate trends
        analytics['trends'] = self._calculate_trends(user_id, days)
        
        # Calculate projections
        analytics['projections'] = self._calculate_projections(user_id, days)
        
        # Calculate insights
        analytics['insights'] = self._generate_insights(analytics)
        
        return {
            'success': True,
            'analytics': analytics
        }
    
    def get_point_type_analytics(self, user_id: str, point_type: str,
                                 days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific point type"""
        if not self.history_tracker:
            return {'success': False, 'error': 'History tracker not available'}
        
        try:
            stats = self.history_tracker.get_point_statistics(user_id, point_type=point_type, days=days)
            
            # Get history for trend analysis
            history = self.history_tracker.get_point_history(user_id, point_type=point_type, limit=1000)
            
            # Calculate trends
            daily_changes = []
            if history.get('history'):
                by_day = defaultdict(float)
                for entry in history['history']:
                    day = entry.get('date', '')
                    by_day[day] += entry.get('amount', 0)
                daily_changes = list(by_day.values())
            
            # Calculate statistics
            if daily_changes:
                avg_daily = statistics.mean(daily_changes)
                median_daily = statistics.median(daily_changes)
                std_daily = statistics.stdev(daily_changes) if len(daily_changes) > 1 else 0
            else:
                avg_daily = median_daily = std_daily = 0
            
            return {
                'success': True,
                'point_type': point_type,
                'statistics': stats,
                'trends': {
                    'average_daily_change': avg_daily,
                    'median_daily_change': median_daily,
                    'std_deviation': std_daily,
                    'daily_changes': daily_changes[-30:]  # Last 30 days
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _calculate_trends(self, user_id: str, days: int) -> Dict[str, Any]:
        """Calculate point trends"""
        if not self.history_tracker:
            return {}
        
        try:
            stats = self.history_tracker.get_point_statistics(user_id, days=days)
            by_day = stats.get('by_day', {})
            
            if not by_day:
                return {'trend': 'stable', 'change_rate': 0}
            
            # Calculate trend
            sorted_days = sorted(by_day.keys())
            if len(sorted_days) < 2:
                return {'trend': 'stable', 'change_rate': 0}
            
            recent_days = sorted_days[-7:]  # Last 7 days
            older_days = sorted_days[:-7] if len(sorted_days) > 7 else []
            
            recent_avg = sum(by_day[d] for d in recent_days) / len(recent_days) if recent_days else 0
            older_avg = sum(by_day[d] for d in older_days) / len(older_days) if older_days else recent_avg
            
            change_rate = ((recent_avg - older_avg) / older_avg * 100) if older_avg != 0 else 0
            
            if change_rate > 5:
                trend = 'increasing'
            elif change_rate < -5:
                trend = 'decreasing'
            else:
                trend = 'stable'
            
            return {
                'trend': trend,
                'change_rate': change_rate,
                'recent_average': recent_avg,
                'older_average': older_avg
            }
        except:
            return {'trend': 'unknown', 'change_rate': 0}
    
    def _calculate_projections(self, user_id: str, days: int) -> Dict[str, Any]:
        """Calculate point projections"""
        if not self.history_tracker:
            return {}
        
        try:
            stats = self.history_tracker.get_point_statistics(user_id, days=days)
            avg_per_day = stats.get('average_per_day', 0)
            
            # Projections for different timeframes
            projections = {
                'next_7_days': avg_per_day * 7,
                'next_30_days': avg_per_day * 30,
                'next_90_days': avg_per_day * 90
            }
            
            return projections
        except:
            return {}
    
    def _generate_insights(self, analytics: Dict[str, Any]) -> List[str]:
        """Generate insights from analytics"""
        insights = []
        
        history_stats = analytics.get('history_stats', {})
        trends = analytics.get('trends', {})
        
        # Trend insights
        trend = trends.get('trend', 'stable')
        change_rate = trends.get('change_rate', 0)
        
        if trend == 'increasing' and change_rate > 10:
            insights.append(f"Strong growth: Points increasing by {change_rate:.1f}%")
        elif trend == 'decreasing' and change_rate < -10:
            insights.append(f"Declining activity: Points decreasing by {abs(change_rate):.1f}%")
        
        # Source insights
        by_source = history_stats.get('by_source', {})
        if by_source:
            top_source = max(by_source.items(), key=lambda x: x[1])
            if top_source[1] > 0:
                insights.append(f"Top earning source: {top_source[0]} ({top_source[1]:.0f} points)")
        
        # Activity insights
        total_earned = history_stats.get('total_earned', 0)
        if total_earned > 1000:
            insights.append(f"High activity: Earned {total_earned:.0f} points in the period")
        
        return insights

# Global instance
point_analytics_dashboard = PointAnalyticsDashboard()

