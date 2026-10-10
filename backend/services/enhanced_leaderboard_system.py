"""
Enhanced Leaderboard System with DB Analysis
Adds context and analyzed data from database
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.ai_intelligence_system import ai_intelligence_system
    unified_points_db = UnifiedPointsDatabase()
except ImportError:
    unified_points_db = None
    ai_intelligence_system = None


class EnhancedLeaderboardSystem:
    """Enhanced leaderboard with DB analysis and context"""
    
    def __init__(self):
        self.leaderboards = {}
        self.analytics_cache = {}
        
    def get_enhanced_leaderboard(self, leaderboard_type: str, limit: int = 100) -> Dict[str, Any]:
        """Get leaderboard with enhanced context and analysis"""
        try:
            # Get base leaderboard
            base_leaderboard = self._get_base_leaderboard(leaderboard_type, limit)
            
            # Add context and analysis
            enhanced = []
            for entry in base_leaderboard.get('entries', []):
                user_id = entry.get('user_id', '')
                
                # Get user analytics
                analytics = self._get_user_analytics(user_id, leaderboard_type)
                
                # Get AI insights
                ai_insights = self._get_ai_insights(user_id, entry)
                
                enhanced_entry = {
                    **entry,
                    'analytics': analytics,
                    'ai_insights': ai_insights,
                    'trend': self._calculate_trend(user_id, leaderboard_type),
                    'context': self._get_user_context(user_id)
                }
                enhanced.append(enhanced_entry)
            
            # Add leaderboard-level analysis
            leaderboard_analysis = self._analyze_leaderboard(enhanced)
            
            return {
                'success': True,
                'leaderboard_type': leaderboard_type,
                'entries': enhanced,
                'analysis': leaderboard_analysis,
                'generated_at': datetime.utcnow().isoformat()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _get_base_leaderboard(self, leaderboard_type: str, limit: int) -> Dict[str, Any]:
        """Get base leaderboard data"""
        # This would query the actual leaderboard
        # For now, return structure
        return {
            'entries': [],
            'total_users': 0
        }
    
    def _get_user_analytics(self, user_id: str, leaderboard_type: str) -> Dict[str, Any]:
        """Get user analytics from DB"""
        if not unified_points_db:
            return {}
        
        try:
            profile = unified_points_db.get_user_profile(user_id)
            preferences = profile.get('preferences', {})
            
            # Analyze point history
            point_history = preferences.get('point_history', [])
            
            analytics = {
                'total_activities': len(point_history),
                'average_points_per_activity': statistics.mean([p.get('amount', 0) for p in point_history]) if point_history else 0,
                'points_trend': self._calculate_points_trend(point_history),
                'activity_frequency': self._calculate_activity_frequency(point_history),
                'peak_performance_time': self._get_peak_performance_time(point_history),
                'improvement_rate': self._calculate_improvement_rate(point_history)
            }
            
            return analytics
        except Exception as e:
            print(f"[EnhancedLeaderboard] Error getting analytics: {e}", flush=True)
            return {}
    
    def _get_ai_insights(self, user_id: str, entry: Dict) -> Dict[str, Any]:
        """Get AI insights for user"""
        if not ai_intelligence_system:
            return {}
        
        try:
            segment = ai_intelligence_system.get_user_segment(user_id)
            
            return {
                'user_segment': segment.get('segment', 'Unknown'),
                'strengths': self._identify_strengths(user_id, entry),
                'recommendations': self._get_recommendations(user_id, entry),
                'predicted_growth': self._predict_growth(user_id)
            }
        except Exception as e:
            return {}
    
    def _calculate_trend(self, user_id: str, leaderboard_type: str) -> str:
        """Calculate user trend (up, down, stable)"""
        # This would compare current vs previous rankings
        return 'stable'
    
    def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context information"""
        if not unified_points_db:
            return {}
        
        try:
            profile = unified_points_db.get_user_profile(user_id)
            
            return {
                'level': profile.get('level', 1),
                'join_date': profile.get('created_at', ''),
                'last_active': profile.get('last_active', ''),
                'achievements_count': len(profile.get('preferences', {}).get('achievements', [])),
                'quests_completed': len([q for q in profile.get('preferences', {}).get('quests', []) if q.get('completed', False)])
            }
        except:
            return {}
    
    def _analyze_leaderboard(self, entries: List[Dict]) -> Dict[str, Any]:
        """Analyze leaderboard data"""
        if not entries:
            return {}
        
        points_list = [e.get('points', 0) for e in entries]
        
        return {
            'total_entries': len(entries),
            'average_points': statistics.mean(points_list) if points_list else 0,
            'median_points': statistics.median(points_list) if points_list else 0,
            'top_percentile': statistics.quantiles(points_list, n=10)[-1] if len(points_list) > 1 else 0,
            'distribution': self._calculate_distribution(points_list)
        }
    
    def _calculate_points_trend(self, point_history: List[Dict]) -> str:
        """Calculate points trend"""
        if len(point_history) < 2:
            return 'insufficient_data'
        
        recent = [p.get('amount', 0) for p in point_history[-10:]]
        older = [p.get('amount', 0) for p in point_history[-20:-10]] if len(point_history) > 10 else []
        
        if not older:
            return 'growing'
        
        recent_avg = statistics.mean(recent) if recent else 0
        older_avg = statistics.mean(older) if older else 0
        
        if recent_avg > older_avg * 1.1:
            return 'growing'
        elif recent_avg < older_avg * 0.9:
            return 'declining'
        else:
            return 'stable'
    
    def _calculate_activity_frequency(self, point_history: List[Dict]) -> Dict[str, Any]:
        """Calculate activity frequency"""
        if not point_history:
            return {'daily': 0, 'weekly': 0}
        
        # Count activities by day
        dates = [datetime.fromisoformat(p.get('timestamp', datetime.utcnow().isoformat())).date() for p in point_history]
        unique_dates = len(set(dates))
        total_days = (datetime.utcnow().date() - min(dates)).days + 1 if dates else 1
        
        return {
            'daily': unique_dates / max(total_days, 1),
            'weekly': unique_dates / max(total_days / 7, 1)
        }
    
    def _get_peak_performance_time(self, point_history: List[Dict]) -> Dict[str, Any]:
        """Get peak performance time"""
        if not point_history:
            return {'hour': 12, 'day': 'any'}
        
        hours = [datetime.fromisoformat(p.get('timestamp', datetime.utcnow().isoformat())).hour for p in point_history]
        
        if hours:
            hour_counts = defaultdict(int)
            for h in hours:
                hour_counts[h] += 1
            
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])[0] if hour_counts else 12
        else:
            peak_hour = 12
        
        return {'hour': peak_hour, 'day': 'any'}
    
    def _calculate_improvement_rate(self, point_history: List[Dict]) -> float:
        """Calculate improvement rate"""
        if len(point_history) < 10:
            return 0.0
        
        recent = [p.get('amount', 0) for p in point_history[-10:]]
        older = [p.get('amount', 0) for p in point_history[-20:-10]] if len(point_history) > 10 else []
        
        if not older:
            return 0.0
        
        recent_avg = statistics.mean(recent) if recent else 0
        older_avg = statistics.mean(older) if older else 0
        
        if older_avg == 0:
            return 0.0
        
        return ((recent_avg - older_avg) / older_avg) * 100
    
    def _identify_strengths(self, user_id: str, entry: Dict) -> List[str]:
        """Identify user strengths"""
        strengths = []
        
        points = entry.get('points', 0)
        if points > 10000:
            strengths.append('High point earner')
        
        # Add more strength identification
        return strengths
    
    def _get_recommendations(self, user_id: str, entry: Dict) -> List[str]:
        """Get recommendations for user"""
        recommendations = []
        
        points = entry.get('points', 0)
        if points < 1000:
            recommendations.append('Complete more quests to earn points')
        
        return recommendations
    
    def _predict_growth(self, user_id: str) -> Dict[str, Any]:
        """Predict user growth"""
        return {
            'predicted_points_30d': 0,
            'confidence': 0.5
        }
    
    def _calculate_distribution(self, points_list: List[float]) -> Dict[str, int]:
        """Calculate points distribution"""
        if not points_list:
            return {}
        
        max_points = max(points_list) if points_list else 1
        ranges = [
            (0, max_points * 0.2, 'low'),
            (max_points * 0.2, max_points * 0.5, 'medium'),
            (max_points * 0.5, max_points * 0.8, 'high'),
            (max_points * 0.8, max_points, 'elite')
        ]
        
        distribution = defaultdict(int)
        for points in points_list:
            for min_val, max_val, label in ranges:
                if min_val <= points < max_val:
                    distribution[label] += 1
                    break
        
        return dict(distribution)


# Global instance
enhanced_leaderboard_system = EnhancedLeaderboardSystem()

