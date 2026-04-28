"""
Social Engagement Agent
Specialized agent for social interactions and engagement
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentSocialEngagement:
    """Social engagement agent"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'social_engagement_agent'
        self.agent_name = 'Social Engagement Agent'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'social_engagement.json')
        self.load_data()
    
    def load_data(self):
        """Load agent data"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = self._default_data()
        else:
            self.data = self._default_data()
            self.save_data()
    
    def _default_data(self) -> Dict:
        """Default agent data"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'level': 1,
            'experience': 0,
            'skills': [
                'manage_friends',
                'coordinate_events',
                'facilitate_discussions',
                'moderate_content',
                'build_community',
                'organize_groups',
                'manage_messages',
                'track_engagement'
            ],
            'friends_managed': 0,
            'events_coordinated': 0,
            'discussions_facilitated': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving social engagement data: {e}")
    
    def coordinate_event(self, event_type: str, parameters: Dict, user_id: str = 'agent_user') -> Dict:
        """Coordinate social event"""
        try:
            from backend.services.agent_point_creator import agent_point_creator
            
            # Award points via trigger
            from backend.services.agent_trigger_system import agent_trigger_system
            agent_trigger_system.award_points('event_participation', self.agent_id, {
                'event_type': event_type,
                'parameters': parameters
            })
            
            # Award points for event coordination - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='coordinate_event',
                user_id=user_id
            )
            
            self.data['events_coordinated'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'event_type': event_type,
                'event_id': f"event_{self.data['events_coordinated']}",
                'total_events': self.data['events_coordinated'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def facilitate_discussion(self, topic: str) -> Dict:
        """Facilitate discussion"""
        try:
            # Award points via trigger
            from backend.services.agent_trigger_system import agent_trigger_system
            agent_trigger_system.award_points('discussion', self.agent_id, {
                'topic': topic
            })
            
            self.data['discussions_facilitated'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'topic': topic,
                'discussion_id': f"disc_{self.data['discussions_facilitated']}",
                'total_discussions': self.data['discussions_facilitated']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'level': self.data.get('level', 1),
            'experience': self.data.get('experience', 0),
            'friends_managed': self.data.get('friends_managed', 0),
            'events_coordinated': self.data.get('events_coordinated', 0),
            'discussions_facilitated': self.data.get('discussions_facilitated', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_social_engagement = AgentSocialEngagement()
