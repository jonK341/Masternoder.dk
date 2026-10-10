"""
Agent Task Force System
Manages agent objectives, missions, and task force operations
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import uuid

class AgentTaskForce:
    """Agent task force management system"""
    
    def __init__(self):
        self.objectives = {}  # {objective_id: objective_data}
        self.missions = {}  # {mission_id: mission_data}
        self.user_objectives = defaultdict(list)  # {user_id: [objective_ids]}
        self.user_missions = defaultdict(list)  # {user_id: [mission_ids]}
        self.calendar_events = defaultdict(list)  # {user_id: [events]}
        self.agent_opinions = defaultdict(list)  # {user_id: [opinions]}
        self.observations = defaultdict(list)  # {user_id: [observations]}
        self.emotions = defaultdict(dict)  # {user_id: emotion_data}
        self.behavior_patterns = defaultdict(dict)  # {user_id: patterns}
    
    def create_objective(self, user_id: str, title: str, description: str,
                        objective_type: str, priority: int, deadline: Optional[datetime]) -> Dict[str, Any]:
        """Create a new objective"""
        objective_id = str(uuid.uuid4())
        objective = {
            'id': objective_id,
            'user_id': user_id,
            'title': title,
            'description': description,
            'type': objective_type,
            'priority': priority,
            'deadline': deadline.isoformat() if deadline else None,
            'status': 'pending',
            'progress': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        self.objectives[objective_id] = objective
        self.user_objectives[user_id].append(objective_id)
        return {'success': True, 'objective': objective}
    
    def assign_objective(self, user_id: str, objective_id: str) -> Dict[str, Any]:
        """Assign objective to user"""
        if objective_id not in self.objectives:
            return {'success': False, 'error': 'Objective not found'}
        self.objectives[objective_id]['user_id'] = user_id
        if objective_id not in self.user_objectives[user_id]:
            self.user_objectives[user_id].append(objective_id)
        return {'success': True, 'objective': self.objectives[objective_id]}
    
    def update_objective_progress(self, user_id: str, objective_id: str, progress: int) -> Dict[str, Any]:
        """Update objective progress"""
        if objective_id not in self.objectives:
            return {'success': False, 'error': 'Objective not found'}
        self.objectives[objective_id]['progress'] = progress
        if progress >= 100:
            self.objectives[objective_id]['status'] = 'completed'
        return {'success': True, 'objective': self.objectives[objective_id]}
    
    def create_mission(self, user_id: str, mission_name: str, mission_type: str,
                      objectives: List, reward_points: int) -> Dict[str, Any]:
        """Create a mission"""
        mission_id = str(uuid.uuid4())
        mission = {
            'id': mission_id,
            'user_id': user_id,
            'name': mission_name,
            'type': mission_type,
            'objectives': objectives,
            'reward_points': reward_points,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        }
        self.missions[mission_id] = mission
        self.user_missions[user_id].append(mission_id)
        return {'success': True, 'mission': mission}
    
    def get_user_objectives(self, user_id: str) -> Dict[str, Any]:
        """Get user objectives"""
        objective_ids = self.user_objectives.get(user_id, [])
        objectives = [self.objectives[oid] for oid in objective_ids if oid in self.objectives]
        return {'success': True, 'objectives': objectives}
    
    def get_user_missions(self, user_id: str) -> Dict[str, Any]:
        """Get user missions"""
        mission_ids = self.user_missions.get(user_id, [])
        missions = [self.missions[mid] for mid in mission_ids if mid in self.missions]
        return {'success': True, 'missions': missions}
    
    def get_calendar_events(self, user_id: str, start_date: Optional[datetime],
                           end_date: Optional[datetime]) -> Dict[str, Any]:
        """Get calendar events"""
        events = self.calendar_events.get(user_id, [])
        if start_date or end_date:
            events = [e for e in events if 
                     (not start_date or e.get('date') >= start_date.isoformat()) and
                     (not end_date or e.get('date') <= end_date.isoformat())]
        return {'success': True, 'events': events}
    
    def record_agent_opinion(self, user_id: str, opinion_type: str, content: str,
                            confidence: float) -> Dict[str, Any]:
        """Record agent opinion"""
        opinion = {
            'type': opinion_type,
            'content': content,
            'confidence': confidence,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.agent_opinions[user_id].append(opinion)
        return {'success': True, 'opinion': opinion}
    
    def record_observation(self, user_id: str, observation_type: str,
                          observation_data: Dict) -> Dict[str, Any]:
        """Record observation"""
        observation = {
            'type': observation_type,
            'data': observation_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.observations[user_id].append(observation)
        return {'success': True, 'observation': observation}
    
    def update_emotion(self, user_id: str, emotion_type: str, intensity: float) -> Dict[str, Any]:
        """Update emotion"""
        self.emotions[user_id][emotion_type] = intensity
        return {'success': True, 'emotion': {emotion_type: intensity}}
    
    def get_emotions(self, user_id: str) -> Dict[str, Any]:
        """Get user emotions"""
        return {'success': True, 'emotions': self.emotions.get(user_id, {})}
    
    def get_behavior_patterns(self, user_id: str) -> Dict[str, Any]:
        """Get behavior patterns"""
        return {'success': True, 'patterns': self.behavior_patterns.get(user_id, {})}

agent_task_force = AgentTaskForce()
