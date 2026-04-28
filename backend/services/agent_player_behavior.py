"""
Agent Player Behavior
Makes agents behave like real players with realistic patterns
"""
import random
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os

class AgentPlayerBehavior:
    """Simulates realistic player behavior for agents"""
    
    def __init__(self):
        self.behavior_patterns = {
            'casual': {
                'login_frequency': (1, 3),  # times per day
                'session_duration': (300, 1800),  # 5-30 minutes
                'actions_per_session': (5, 20),
                'time_between_actions': (30, 180),  # seconds
                'preferred_activities': ['browse', 'watch', 'social'],
                'active_hours': [(9, 12), (18, 22)]  # morning and evening
            },
            'active': {
                'login_frequency': (3, 6),
                'session_duration': (600, 3600),  # 10-60 minutes
                'actions_per_session': (15, 50),
                'time_between_actions': (10, 60),
                'preferred_activities': ['battle', 'generate', 'quest', 'social'],
                'active_hours': [(8, 23)]  # most of the day
            },
            'hardcore': {
                'login_frequency': (5, 10),
                'session_duration': (1800, 7200),  # 30-120 minutes
                'actions_per_session': (30, 100),
                'time_between_actions': (5, 30),
                'preferred_activities': ['battle', 'generate', 'quest', 'battle', 'battle'],
                'active_hours': [(0, 23)]  # all day
            },
            'social': {
                'login_frequency': (2, 5),
                'session_duration': (400, 2400),
                'actions_per_session': (10, 40),
                'time_between_actions': (20, 120),
                'preferred_activities': ['social', 'chat', 'share', 'browse'],
                'active_hours': [(12, 14), (19, 23)]
            }
        }
        
        self.activity_types = {
            'browse': {
                'xp_gain': (5, 20),
                'points_gain': (1, 5),
                'duration': (30, 180)
            },
            'watch': {
                'xp_gain': (10, 50),
                'points_gain': (2, 10),
                'duration': (60, 600)
            },
            'generate': {
                'xp_gain': (50, 200),
                'points_gain': (10, 50),
                'duration': (120, 600)
            },
            'battle': {
                'xp_gain': (30, 150),
                'points_gain': (5, 25),
                'duration': (60, 300)
            },
            'quest': {
                'xp_gain': (20, 100),
                'points_gain': (3, 15),
                'duration': (90, 450)
            },
            'social': {
                'xp_gain': (5, 30),
                'points_gain': (1, 8),
                'duration': (30, 240)
            },
            'chat': {
                'xp_gain': (3, 15),
                'points_gain': (1, 3),
                'duration': (60, 300)
            },
            'share': {
                'xp_gain': (10, 40),
                'points_gain': (2, 8),
                'duration': (30, 120)
            }
        }
    
    def get_behavior_type(self, agent_id: str) -> str:
        """Determine agent's behavior type based on ID or random"""
        # Use agent_id hash to get consistent behavior
        hash_val = hash(agent_id) % 100
        if hash_val < 40:
            return 'casual'
        elif hash_val < 70:
            return 'active'
        elif hash_val < 85:
            return 'hardcore'
        else:
            return 'social'
    
    def should_be_active_now(self, behavior_type: str) -> bool:
        """Check if agent should be active based on current time and behavior"""
        current_hour = datetime.now().hour
        active_hours = self.behavior_patterns[behavior_type]['active_hours']
        
        for start, end in active_hours:
            if start <= current_hour < end:
                return True
        return False
    
    def generate_session_plan(self, agent_id: str, behavior_type: Optional[str] = None) -> Dict:
        """Generate a realistic session plan for an agent"""
        if not behavior_type:
            behavior_type = self.get_behavior_type(agent_id)
        
        pattern = self.behavior_patterns[behavior_type]
        
        # Determine session start time (within active hours)
        current_hour = datetime.now().hour
        active_hours = pattern['active_hours']
        session_hour = None
        
        for start, end in active_hours:
            if start <= current_hour < end:
                session_hour = current_hour
                break
        
        if session_hour is None:
            # Use first available active hour
            session_hour = active_hours[0][0]
        
        session_start = datetime.now().replace(hour=session_hour, minute=random.randint(0, 59))
        
        # Generate actions for this session
        num_actions = random.randint(*pattern['actions_per_session'])
        actions = []
        
        for i in range(num_actions):
            action_type = random.choice(pattern['preferred_activities'])
            action_time = session_start + timedelta(
                seconds=sum([random.randint(*pattern['time_between_actions']) for _ in range(i)])
            )
            
            activity_data = self.activity_types[action_type]
            
            actions.append({
                'type': action_type,
                'timestamp': action_time.isoformat(),
                'xp_gain': random.randint(*activity_data['xp_gain']),
                'points_gain': random.randint(*activity_data['points_gain']),
                'duration': random.randint(*activity_data['duration'])
            })
        
        session_duration = random.randint(*pattern['session_duration'])
        
        return {
            'agent_id': agent_id,
            'behavior_type': behavior_type,
            'session_start': session_start.isoformat(),
            'session_duration': session_duration,
            'actions': actions,
            'total_xp': sum(a['xp_gain'] for a in actions),
            'total_points': sum(a['points_gain'] for a in actions)
        }
    
    def execute_action(self, agent_id: str, action: Dict) -> Dict:
        """Execute a single action and return results"""
        action_type = action['type']
        
        # Simulate realistic delays
        time.sleep(random.uniform(0.1, 0.5))
        
        # Generate action result
        result = {
            'agent_id': agent_id,
            'action_type': action_type,
            'timestamp': datetime.now().isoformat(),
            'xp_gained': action['xp_gain'],
            'points_gained': action['points_gain'],
            'duration': action['duration'],
            'success': random.random() > 0.05,  # 95% success rate
            'details': self._generate_action_details(action_type)
        }
        
        return result
    
    def _generate_action_details(self, action_type: str) -> Dict:
        """Generate realistic details for an action"""
        details = {
            'browse': {
                'pages_visited': random.randint(2, 8),
                'time_on_site': random.randint(60, 600)
            },
            'watch': {
                'video_id': f"video_{random.randint(1000, 9999)}",
                'watch_percentage': random.randint(20, 100),
                'liked': random.random() > 0.7
            },
            'generate': {
                'video_created': True,
                'template_used': random.choice(['template1', 'template2', 'template3']),
                'quality_score': random.randint(70, 100)
            },
            'battle': {
                'opponent_id': f"player_{random.randint(1, 100)}",
                'result': random.choice(['win', 'win', 'win', 'loss']),  # 75% win rate
                'damage_dealt': random.randint(100, 1000),
                'damage_taken': random.randint(50, 800)
            },
            'quest': {
                'quest_id': f"quest_{random.randint(1, 50)}",
                'completed': random.random() > 0.2,  # 80% completion
                'objectives_done': random.randint(1, 5)
            },
            'social': {
                'interaction_type': random.choice(['like', 'comment', 'share', 'follow']),
                'target_user': f"user_{random.randint(1, 100)}",
                'engagement_score': random.randint(1, 10)
            },
            'chat': {
                'messages_sent': random.randint(1, 10),
                'conversation_partners': random.randint(1, 5),
                'topics': random.sample(['gaming', 'videos', 'battles', 'quests'], random.randint(1, 3))
            },
            'share': {
                'content_shared': random.choice(['video', 'achievement', 'battle_result']),
                'platform': random.choice(['internal', 'twitter', 'facebook']),
                'reach': random.randint(10, 1000)
            }
        }
        
        return details.get(action_type, {})
    
    def simulate_daily_activity(self, agent_id: str) -> Dict:
        """Simulate a full day of agent activity"""
        behavior_type = self.get_behavior_type(agent_id)
        login_frequency = random.randint(*self.behavior_patterns[behavior_type]['login_frequency'])
        
        sessions = []
        total_xp = 0
        total_points = 0
        
        for i in range(login_frequency):
            session_plan = self.generate_session_plan(agent_id, behavior_type)
            sessions.append(session_plan)
            total_xp += session_plan['total_xp']
            total_points += session_plan['total_points']
        
        return {
            'agent_id': agent_id,
            'behavior_type': behavior_type,
            'date': datetime.now().date().isoformat(),
            'sessions': sessions,
            'total_sessions': len(sessions),
            'total_xp': total_xp,
            'total_points': total_points,
            'total_actions': sum(len(s['actions']) for s in sessions)
        }
    
    def execute_session(self, agent_id: str, session_plan: Dict) -> List[Dict]:
        """Execute all actions in a session plan"""
        results = []
        
        for action in session_plan['actions']:
            result = self.execute_action(agent_id, action)
            results.append(result)
            
            # Realistic delay between actions
            delay = random.uniform(0.5, 2.0)
            time.sleep(min(delay, 0.1))  # Cap at 0.1s for testing
        
        return results

# Global instance
agent_player_behavior = AgentPlayerBehavior()
