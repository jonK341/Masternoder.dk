"""
System History & Psychology
Tracks system changes, user progression, and provides psychological insights
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class SystemHistory:
    """Tracks system history and user progression"""
    
    def __init__(self):
        self.history_entries = []  # System-wide history
        self.user_timelines = {}  # user_id -> [timeline_entries]
        self.achievement_milestones = {}  # user_id -> [milestones]
        self.system_evolution = []  # System changes over time
    
    def log_system_change(self, change_type: str, description: str, metadata: Dict[str, Any] = None):
        """Log a system-wide change"""
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'change_type': change_type,  # feature_added, point_system_updated, etc.
            'description': description,
            'metadata': metadata or {}
        }
        self.history_entries.append(entry)
        self.system_evolution.append(entry)
        logger.info(f"System change logged: {change_type} - {description}")
    
    def log_user_progression(self, user_id: str, event_type: str, event_data: Dict[str, Any]):
        """Log user progression event"""
        if user_id not in self.user_timelines:
            self.user_timelines[user_id] = []
        
        entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': event_type,  # level_up, point_milestone, achievement_unlocked, etc.
            'event_data': event_data
        }
        self.user_timelines[user_id].append(entry)
    
    def add_milestone(self, user_id: str, milestone_type: str, milestone_data: Dict[str, Any]):
        """Add achievement milestone"""
        if user_id not in self.achievement_milestones:
            self.achievement_milestones[user_id] = []
        
        milestone = {
            'timestamp': datetime.utcnow().isoformat(),
            'milestone_type': milestone_type,
            'milestone_data': milestone_data
        }
        self.achievement_milestones[user_id].append(milestone)
    
    def get_user_timeline(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get user progression timeline"""
        timeline = self.user_timelines.get(user_id, [])
        return timeline[-limit:] if limit else timeline
    
    def get_system_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get system-wide history"""
        return self.history_entries[-limit:] if limit else self.history_entries
    
    def get_user_milestones(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user achievement milestones"""
        return self.achievement_milestones.get(user_id, [])

class PsychologySystem:
    """Provides psychological insights and behavior analysis"""
    
    def __init__(self):
        self.user_behaviors = {}  # user_id -> behavior_data
        self.engagement_patterns = {}  # user_id -> patterns
        self.motivation_tracking = {}  # user_id -> motivation_data
    
    def analyze_behavior(self, user_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze user behavior patterns"""
        if user_id not in self.user_behaviors:
            self.user_behaviors[user_id] = {
                'total_activities': 0,
                'activity_types': {},
                'peak_hours': {},
                'engagement_score': 0,
                'consistency_score': 0
            }
        
        behavior = self.user_behaviors[user_id]
        behavior['total_activities'] += 1
        
        # Track activity types
        activity_type = activity_data.get('type', 'unknown')
        behavior['activity_types'][activity_type] = behavior['activity_types'].get(activity_type, 0) + 1
        
        # Track peak hours
        hour = datetime.utcnow().hour
        behavior['peak_hours'][hour] = behavior['peak_hours'].get(hour, 0) + 1
        
        # Calculate engagement score (0-100)
        behavior['engagement_score'] = min(100, behavior['total_activities'] / 10)
        
        return {
            'user_id': user_id,
            'behavior_summary': behavior,
            'insights': self._generate_insights(behavior)
        }
    
    def track_motivation(self, user_id: str, point_gain: float, activity_type: str):
        """Track user motivation patterns"""
        if user_id not in self.motivation_tracking:
            self.motivation_tracking[user_id] = {
                'total_points': 0,
                'point_gains': [],
                'preferred_activities': {},
                'motivation_level': 'medium'
            }
        
        motivation = self.motivation_tracking[user_id]
        motivation['total_points'] += point_gain
        motivation['point_gains'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'points': point_gain,
            'activity': activity_type
        })
        
        # Track preferred activities
        motivation['preferred_activities'][activity_type] = \
            motivation['preferred_activities'].get(activity_type, 0) + point_gain
        
        # Calculate motivation level
        recent_gains = motivation['point_gains'][-10:]
        avg_gain = sum(g['points'] for g in recent_gains) / len(recent_gains) if recent_gains else 0
        
        if avg_gain > 100:
            motivation['motivation_level'] = 'high'
        elif avg_gain > 50:
            motivation['motivation_level'] = 'medium'
        else:
            motivation['motivation_level'] = 'low'
        
        return motivation
    
    def _generate_insights(self, behavior: Dict[str, Any]) -> List[str]:
        """Generate psychological insights"""
        insights = []
        
        total = behavior['total_activities']
        if total > 1000:
            insights.append("Highly engaged user - consistent participation")
        elif total > 500:
            insights.append("Active user - good engagement patterns")
        
        # Peak hours analysis
        if behavior['peak_hours']:
            peak_hour = max(behavior['peak_hours'].items(), key=lambda x: x[1])[0]
            insights.append(f"Most active during hour {peak_hour}:00")
        
        # Activity diversity
        activity_count = len(behavior['activity_types'])
        if activity_count > 10:
            insights.append("Diverse activity patterns - exploring multiple features")
        elif activity_count > 5:
            insights.append("Moderate activity diversity")
        
        return insights
    
    def get_psychological_profile(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive psychological profile"""
        behavior = self.user_behaviors.get(user_id, {})
        motivation = self.motivation_tracking.get(user_id, {})
        
        return {
            'user_id': user_id,
            'behavior_analysis': behavior,
            'motivation_profile': motivation,
            'engagement_level': self._calculate_engagement_level(behavior),
            'recommendations': self._generate_recommendations(behavior, motivation)
        }
    
    def _calculate_engagement_level(self, behavior: Dict[str, Any]) -> str:
        """Calculate engagement level"""
        score = behavior.get('engagement_score', 0)
        if score >= 80:
            return 'very_high'
        elif score >= 60:
            return 'high'
        elif score >= 40:
            return 'medium'
        elif score >= 20:
            return 'low'
        else:
            return 'very_low'
    
    def _generate_recommendations(self, behavior: Dict[str, Any], motivation: Dict[str, Any]) -> List[str]:
        """Generate personalized recommendations"""
        recommendations = []
        
        engagement = behavior.get('engagement_score', 0)
        if engagement < 30:
            recommendations.append("Try exploring different features to increase engagement")
        
        motivation_level = motivation.get('motivation_level', 'medium')
        if motivation_level == 'low':
            recommendations.append("Focus on activities that provide higher point rewards")
        
        # Activity diversity recommendations
        activity_count = len(behavior.get('activity_types', {}))
        if activity_count < 5:
            recommendations.append("Explore more activity types to diversify your experience")
        
        return recommendations

system_history = SystemHistory()
psychology_system = PsychologySystem()
