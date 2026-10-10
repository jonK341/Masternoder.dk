"""
Social Points System
Tracks social interactions, connections, and community engagement
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SocialPointsSystem:
    """
    Social Points System
    Tracks and rewards social engagement
    """
    
    def __init__(self):
        self.social_points = {}
        self.friendships = {}
        self.community_activities = {}
        self.social_events = []
    
    def add_social_points(self, user_id: str, points: float, 
                         activity_type: str, metadata: Dict = None) -> Dict[str, Any]:
        """
        Add social points to user
        """
        if user_id not in self.social_points:
            self.social_points[user_id] = {
                'total_points': 0.0,
                'activity_points': {},
                'friendship_points': 0.0,
                'community_points': 0.0,
                'event_points': 0.0,
                'last_updated': datetime.utcnow().isoformat()
            }
        
        user_points = self.social_points[user_id]
        user_points['total_points'] += points
        
        # Categorize points
        if activity_type == 'friendship':
            user_points['friendship_points'] += points
        elif activity_type == 'community':
            user_points['community_points'] += points
        elif activity_type == 'event':
            user_points['event_points'] += points
        else:
            if activity_type not in user_points['activity_points']:
                user_points['activity_points'][activity_type] = 0.0
            user_points['activity_points'][activity_type] += points
        
        user_points['last_updated'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'user_id': user_id,
            'points_added': points,
            'total_points': user_points['total_points'],
            'activity_type': activity_type
        }
    
    def create_friendship(self, user1_id: str, user2_id: str) -> Dict[str, Any]:
        """
        Create friendship between two users
        """
        friendship_id = f"friendship_{user1_id}_{user2_id}"
        
        friendship = {
            'id': friendship_id,
            'user1': user1_id,
            'user2': user2_id,
            'created_at': datetime.utcnow().isoformat(),
            'strength': 1.0,
            'interactions': 0
        }
        
        self.friendships[friendship_id] = friendship
        
        # Award friendship points
        self.add_social_points(user1_id, 10.0, 'friendship')
        self.add_social_points(user2_id, 10.0, 'friendship')
        
        return {'success': True, 'friendship': friendship}
    
    def record_community_activity(self, user_id: str, activity_type: str,
                                 points: float) -> Dict[str, Any]:
        """
        Record community activity
        """
        activity = {
            'user_id': user_id,
            'activity_type': activity_type,
            'points': points,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if user_id not in self.community_activities:
            self.community_activities[user_id] = []
        
        self.community_activities[user_id].append(activity)
        
        # Add social points
        self.add_social_points(user_id, points, 'community')
        
        return {'success': True, 'activity': activity}
    
    def get_social_points(self, user_id: str) -> Dict[str, Any]:
        """
        Get social points for user
        """
        if user_id not in self.social_points:
            return {
                'success': True,
                'user_id': user_id,
                'total_points': 0.0,
                'breakdown': {}
            }
        
        user_points = self.social_points[user_id]
        
        return {
            'success': True,
            'user_id': user_id,
            'total_points': user_points['total_points'],
            'breakdown': {
                'friendship_points': user_points['friendship_points'],
                'community_points': user_points['community_points'],
                'event_points': user_points['event_points'],
                'activity_points': user_points['activity_points']
            }
        }

# Global instance
social_points_system = SocialPointsSystem()

