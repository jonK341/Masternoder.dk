"""
Point Generation from Activities
Generate points from various user activities
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import uuid

class PointGenerationActivities:
    """Generate points from user activities"""
    
    def __init__(self):
        self.activity_point_values = {
            'video_generation': {
                'base_points': 50,
                'xp_points': 100,
                'generation_points': 25,
                'activity_points': 10
            },
            'battle_victory': {
                'base_points': 30,
                'xp_points': 50,
                'battle_points': 20,
                'activity_points': 5
            },
            'battle_loss': {
                'base_points': 10,
                'xp_points': 20,
                'battle_points': 5,
                'activity_points': 2
            },
            'quest_completion': {
                'base_points': 40,
                'xp_points': 75,
                'quest_points': 30,
                'activity_points': 8
            },
            'knowledge_unlock': {
                'base_points': 25,
                'xp_points': 50,
                'knowledge_points': 20,
                'activity_points': 5
            },
            'trophy_earned': {
                'base_points': 60,
                'xp_points': 100,
                'trophy_points': 50,
                'activity_points': 15
            },
            'top50_rank_up': {
                'base_points': 100,
                'xp_points': 200,
                'ranking_points': 75,
                'activity_points': 25
            },
            'cash_generation': {
                'base_points': 5,
                'xp_points': 10,
                'cash_points': 3,
                'activity_points': 2
            }
        }
        
        self.activity_history = {}  # user_id -> [activities]
    
    def generate_points_from_activity(self, user_id: str, activity_type: str, 
                                     metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate points from an activity"""
        if activity_type not in self.activity_point_values:
            return {'success': False, 'error': 'Invalid activity type'}
        
        point_config = self.activity_point_values[activity_type]
        metadata = metadata or {}
        
        # Calculate multipliers with enhanced system
        quality_multiplier = metadata.get('quality', 1.0)
        difficulty_multiplier = metadata.get('difficulty_multiplier', 1.0)
        bonus_multiplier = metadata.get('bonus_multiplier', 1.0)
        
        # Additional multipliers
        streak_multiplier = 1.0 + (metadata.get('streak', 0) * 0.01)  # 1% per streak
        level_multiplier = 1.0 + (metadata.get('level', 1) * 0.005)    # 0.5% per level
        premium_multiplier = metadata.get('premium', 1.0)               # Premium user bonus
        event_multiplier = metadata.get('event', 1.0)                   # Event bonus
        
        total_multiplier = (quality_multiplier * difficulty_multiplier * bonus_multiplier * 
                           streak_multiplier * level_multiplier * premium_multiplier * event_multiplier)
        
        # Generate points
        points_generated = {}
        for point_type, base_value in point_config.items():
            points_generated[point_type] = int(base_value * total_multiplier)
        
        # Record activity
        activity = {
            'activity_id': str(uuid.uuid4()),
            'user_id': user_id,
            'activity_type': activity_type,
            'points_generated': points_generated,
            'metadata': metadata,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if user_id not in self.activity_history:
            self.activity_history[user_id] = []
        self.activity_history[user_id].append(activity)
        
        # Record in history
        try:
            from backend.services.point_history_tracking import point_history_tracking
            for point_type, amount in points_generated.items():
                point_history_tracking.record_point_change(
                    user_id, point_type, amount, 
                    source=f"activity_{activity_type}",
                    metadata=metadata
                )
        except Exception as e:
            print(f"Error recording point history: {e}")
        
        # Add points to unified system
        try:
            from backend.services.unified_point_system_json_storage import unified_point_system
            
            for point_type, amount in points_generated.items():
                if point_type != 'base_points':
                    unified_point_system.increment_points(
                        user_id, amount, point_type.replace('_points', '')
                    )
        except Exception as e:
            print(f"Error adding points to unified system: {e}")
        
        return {
            'success': True,
            'activity': activity,
            'points_generated': points_generated,
            'total_points': sum(points_generated.values())
        }
    
    def get_activity_history(self, user_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get user activity history"""
        activities = self.activity_history.get(user_id, [])
        activities.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return {
            'success': True,
            'activities': activities[:limit],
            'total': len(activities),
            'total_points_earned': sum(
                sum(a['points_generated'].values()) for a in activities
            )
        }
    
    def get_activity_statistics(self, user_id: str) -> Dict[str, Any]:
        """Get activity statistics"""
        activities = self.activity_history.get(user_id, [])
        
        stats = {
            'total_activities': len(activities),
            'by_type': {},
            'total_points': 0,
            'most_common_activity': None,
            'recent_activities': activities[-10:] if activities else []
        }
        
        for activity in activities:
            activity_type = activity['activity_type']
            stats['by_type'][activity_type] = stats['by_type'].get(activity_type, 0) + 1
            stats['total_points'] += sum(activity['points_generated'].values())
        
        if stats['by_type']:
            stats['most_common_activity'] = max(
                stats['by_type'].items(), 
                key=lambda x: x[1]
            )[0]
        
        return {
            'success': True,
            'statistics': stats
        }

# Global instance
point_generation_activities = PointGenerationActivities()

