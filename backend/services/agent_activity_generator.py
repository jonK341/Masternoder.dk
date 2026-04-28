"""
Agent Activity Generator
Generates diverse activities for agents with personality and behavior patterns
"""
import random
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

class AgentActivityGenerator:
    """Generate activities for agents based on personality"""
    
    def __init__(self):
        self.activity_types = [
            'diagnostic',
            'maintenance',
            'monitoring',
            'optimization',
            'research',
            'exploration',
            'collaboration',
            'learning',
            'innovation',
            'problem_solving'
        ]
        
        self.personality_activities = {
            'analytical': ['diagnostic', 'research', 'monitoring', 'problem_solving'],
            'aggressive': ['optimization', 'maintenance', 'problem_solving', 'innovation'],
            'cautious': ['monitoring', 'diagnostic', 'research', 'collaboration'],
            'creative': ['innovation', 'exploration', 'learning', 'collaboration'],
            'balanced': self.activity_types
        }
        
        self.behavior_patterns = {
            'comprehensive': {
                'detail_level': 'high',
                'frequency': 'regular',
                'scope': 'full'
            },
            'focused': {
                'detail_level': 'medium',
                'frequency': 'frequent',
                'scope': 'targeted'
            },
            'minimal': {
                'detail_level': 'low',
                'frequency': 'occasional',
                'scope': 'essential'
            }
        }
    
    def generate_activity(self, personality_type: str = 'analytical', behavior: str = 'comprehensive') -> Dict:
        """Generate a random activity based on personality"""
        available_activities = self.personality_activities.get(personality_type, self.activity_types)
        activity_type = random.choice(available_activities)
        
        behavior_config = self.behavior_patterns.get(behavior, self.behavior_patterns['comprehensive'])
        
        activity = {
            'id': f"activity_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000, 9999)}",
            'type': activity_type,
            'name': self._get_activity_name(activity_type),
            'description': self._get_activity_description(activity_type),
            'personality_type': personality_type,
            'behavior': behavior,
            'behavior_config': behavior_config,
            'created_at': datetime.now().isoformat(),
            'estimated_duration': random.randint(5, 30),  # minutes
            'priority': random.choice(['low', 'medium', 'high']),
            'complexity': random.choice(['simple', 'moderate', 'complex']),
            'rewards': {
                'experience': random.randint(10, 50),
                'points': random.randint(5, 25)
            }
        }
        
        return activity
    
    def _get_activity_name(self, activity_type: str) -> str:
        """Get activity name"""
        names = {
            'diagnostic': 'System Diagnostic Scan',
            'maintenance': 'Routine Maintenance Check',
            'monitoring': 'Continuous Monitoring Cycle',
            'optimization': 'Performance Optimization',
            'research': 'Code Structure Research',
            'exploration': 'API Endpoint Exploration',
            'collaboration': 'Cross-System Collaboration',
            'learning': 'Pattern Learning Session',
            'innovation': 'Innovative Solution Design',
            'problem_solving': 'Issue Resolution Task'
        }
        return names.get(activity_type, 'General Activity')
    
    def _get_activity_description(self, activity_type: str) -> str:
        """Get activity description"""
        descriptions = {
            'diagnostic': 'Perform comprehensive system diagnostic to identify issues',
            'maintenance': 'Execute routine maintenance tasks to keep system healthy',
            'monitoring': 'Monitor system metrics and generate alerts if needed',
            'optimization': 'Optimize system performance and resource usage',
            'research': 'Research code structure and identify improvement opportunities',
            'exploration': 'Explore API endpoints and discover new capabilities',
            'collaboration': 'Collaborate with other systems to share insights',
            'learning': 'Learn from patterns and improve decision making',
            'innovation': 'Design innovative solutions to complex problems',
            'problem_solving': 'Solve specific issues and implement fixes'
        }
        return descriptions.get(activity_type, 'General activity description')
    
    def generate_activity_sequence(self, count: int = 5, personality_type: str = 'analytical') -> List[Dict]:
        """Generate a sequence of activities"""
        activities = []
        for i in range(count):
            activity = self.generate_activity(personality_type)
            activity['sequence_order'] = i + 1
            activities.append(activity)
        
        return activities
    
    def generate_daily_activities(self, personality_type: str = 'analytical') -> Dict:
        """Generate daily activity plan"""
        activities = self.generate_activity_sequence(8, personality_type)
        
        return {
            'date': datetime.now().date().isoformat(),
            'personality_type': personality_type,
            'total_activities': len(activities),
            'activities': activities,
            'estimated_total_time': sum(a['estimated_duration'] for a in activities),
            'total_rewards': {
                'experience': sum(a['rewards']['experience'] for a in activities),
                'points': sum(a['rewards']['points'] for a in activities)
            }
        }
    
    def generate_weekly_mission(self, personality_type: str = 'analytical') -> Dict:
        """Generate weekly mission"""
        daily_plans = []
        for i in range(7):
            plan = self.generate_daily_activities(personality_type)
            plan['day'] = i + 1
            daily_plans.append(plan)
        
        total_experience = sum(plan['total_rewards']['experience'] for plan in daily_plans)
        total_points = sum(plan['total_rewards']['points'] for plan in daily_plans)
        
        return {
            'id': f"weekly_mission_{datetime.now().strftime('%Y%W')}",
            'name': 'Weekly Maintenance Mission',
            'description': 'Complete all daily activities for the week',
            'personality_type': personality_type,
            'start_date': datetime.now().date().isoformat(),
            'end_date': (datetime.now() + timedelta(days=7)).date().isoformat(),
            'daily_plans': daily_plans,
            'total_activities': sum(plan['total_activities'] for plan in daily_plans),
            'total_rewards': {
                'experience': total_experience,
                'points': total_points,
                'achievement': 'Weekly Warrior'
            }
        }

# Global instance
agent_activity_generator = AgentActivityGenerator()
