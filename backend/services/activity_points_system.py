"""
Activity Points System for Visitors
Tracks visitor activity and awards points for engagement
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json


class ActivityPointsSystem:
    """Tracks visitor activity and awards activity points"""
    
    def __init__(self):
        self.visitor_data = {}  # {visitor_id: VisitorProfile}
        self.activity_log = defaultdict(list)  # {visitor_id: [activities]}
        self.points_history = defaultdict(list)  # {visitor_id: [point_events]}
        
    def track_visitor(self, visitor_id: str, activity_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Track visitor activity and award points
        
        Args:
            visitor_id: Unique visitor identifier (can be session_id or user_id)
            activity_type: Type of activity (page_view, click, scroll, time_spent, etc.)
            metadata: Additional activity metadata
        
        Returns:
            Activity tracking result with points awarded
        """
        if metadata is None:
            metadata = {}
        
        # Initialize visitor profile if needed
        if visitor_id not in self.visitor_data:
            self.visitor_data[visitor_id] = {
                'visitor_id': visitor_id,
                'first_seen': datetime.utcnow().isoformat(),
                'last_seen': datetime.utcnow().isoformat(),
                'total_points': 0,
                'total_activities': 0,
                'session_count': 1,
                'total_time_spent': 0,
                'activity_types': defaultdict(int)
            }
        
        visitor = self.visitor_data[visitor_id]
        visitor['last_seen'] = datetime.utcnow().isoformat()
        visitor['total_activities'] += 1
        visitor['activity_types'][activity_type] += 1
        
        # Calculate points based on activity type
        points = self._calculate_activity_points(activity_type, metadata)
        visitor['total_points'] += points
        
        # Log activity
        activity = {
            'timestamp': datetime.utcnow().isoformat(),
            'activity_type': activity_type,
            'points_awarded': points,
            'metadata': metadata
        }
        self.activity_log[visitor_id].append(activity)
        
        # Log points event
        point_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'points': points,
            'activity_type': activity_type,
            'total_points': visitor['total_points']
        }
        self.points_history[visitor_id].append(point_event)
        
        return {
            'success': True,
            'points_awarded': points,
            'total_points': visitor['total_points'],
            'activity': activity
        }
    
    def _calculate_activity_points(self, activity_type: str, metadata: Dict[str, Any]) -> int:
        """Calculate points for different activity types"""
        base_points = {
            'page_view': 1,
            'click': 2,
            'scroll': 1,
            'time_spent_30s': 5,
            'time_spent_1m': 10,
            'time_spent_5m': 25,
            'time_spent_10m': 50,
            'battle_participation': 20,
            'battle_victory': 50,
            'battle_defeat': 10,
            'social_interaction': 15,
            'video_watch': 5,
            'video_share': 20,
            'achievement_unlock': 100,
            'daily_login': 25,
            'streak_bonus': 50,
            'return_visitor': 10,
        }
        
        points = base_points.get(activity_type, 1)
        
        # Apply multipliers
        if metadata:
            # Streak bonus
            if metadata.get('streak_days', 0) > 0:
                points += metadata['streak_days'] * 5
            
            # Time spent bonus
            if 'time_spent_seconds' in metadata:
                time_bonus = metadata['time_spent_seconds'] // 60  # 1 point per minute
                points += time_bonus
            
            # Engagement bonus
            if metadata.get('high_engagement', False):
                points = int(points * 1.5)
        
        return points
    
    def track_time_spent(self, visitor_id: str, seconds: int) -> Dict[str, Any]:
        """Track time spent on page"""
        visitor = self.visitor_data.get(visitor_id, {})
        visitor['total_time_spent'] = visitor.get('total_time_spent', 0) + seconds
        
        # Award points based on time milestones
        points = 0
        activity_type = None
        
        if seconds >= 600:  # 10 minutes
            points = 50
            activity_type = 'time_spent_10m'
        elif seconds >= 300:  # 5 minutes
            points = 25
            activity_type = 'time_spent_5m'
        elif seconds >= 60:  # 1 minute
            points = 10
            activity_type = 'time_spent_1m'
        elif seconds >= 30:  # 30 seconds
            points = 5
            activity_type = 'time_spent_30s'
        
        if activity_type:
            return self.track_visitor(visitor_id, activity_type, {
                'time_spent_seconds': seconds
            })
        
        return {'success': True, 'points_awarded': 0}
    
    def get_visitor_stats(self, visitor_id: str) -> Dict[str, Any]:
        """Get comprehensive visitor statistics"""
        if visitor_id not in self.visitor_data:
            return {
                'success': False,
                'error': 'Visitor not found'
            }
        
        visitor = self.visitor_data[visitor_id].copy()
        # Convert defaultdict to regular dict for JSON serialization
        if 'activity_types' in visitor and isinstance(visitor['activity_types'], defaultdict):
            visitor['activity_types'] = dict(visitor['activity_types'])
        
        recent_activities = self.activity_log[visitor_id][-10:]  # Last 10 activities
        
        return {
            'success': True,
            'visitor': visitor,
            'recent_activities': recent_activities,
            'total_activities': len(self.activity_log[visitor_id]),
            'points_history': self.points_history[visitor_id][-20:]  # Last 20 point events
        }
    
    def get_leaderboard(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get activity points leaderboard"""
        try:
            visitors = []
            for visitor in self.visitor_data.values():
                visitor_copy = visitor.copy()
                # Convert defaultdict to regular dict for JSON serialization
                if 'activity_types' in visitor_copy and isinstance(visitor_copy['activity_types'], defaultdict):
                    visitor_copy['activity_types'] = dict(visitor_copy['activity_types'])
                visitors.append(visitor_copy)
            
            sorted_visitors = sorted(visitors, key=lambda x: x.get('total_points', 0), reverse=True)
            return sorted_visitors[:limit]
        except Exception as e:
            # Return empty list on error
            return []


# Global instance
activity_points_system = ActivityPointsSystem()

