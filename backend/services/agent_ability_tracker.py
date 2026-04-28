"""
Agent Ability Tracker
Tracks agent abilities, skill usage, performance, and progress
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentAbilityTracker:
    """Tracks agent abilities and performance"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.tracker_file = os.path.join(self.base_dir, 'logs', 'agent_ability_tracker', 'tracker.json')
        self.load_tracker()
    
    def load_tracker(self):
        """Load tracker data"""
        os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    self.tracker = json.load(f)
            except:
                self.tracker = self._default_tracker()
        else:
            self.tracker = self._default_tracker()
            self.save_tracker()
    
    def _default_tracker(self) -> Dict:
        """Default tracker data"""
        return {
            'agents': {},
            'skill_usage': {},
            'performance_metrics': {},
            'ability_history': [],
            'skill_statistics': {},
            'last_updated': datetime.now().isoformat()
        }
    
    def save_tracker(self):
        """Save tracker data"""
        try:
            self.tracker['last_updated'] = datetime.now().isoformat()
            with open(self.tracker_file, 'w') as f:
                json.dump(self.tracker, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving tracker: {e}")
    
    def track_skill_usage(self, agent_id: str, skill: str, success: bool = True, metadata: Dict = None):
        """Track skill usage"""
        if agent_id not in self.tracker['agents']:
            self.tracker['agents'][agent_id] = {
                'skill_count': {},
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'last_activity': None
            }
        
        agent_data = self.tracker['agents'][agent_id]
        agent_data['total_executions'] = agent_data.get('total_executions', 0) + 1
        
        if success:
            agent_data['successful_executions'] = agent_data.get('successful_executions', 0) + 1
        else:
            agent_data['failed_executions'] = agent_data.get('failed_executions', 0) + 1
        
        # Track skill usage
        if skill not in agent_data['skill_count']:
            agent_data['skill_count'][skill] = {
                'count': 0,
                'success': 0,
                'failure': 0,
                'last_used': None
            }
        
        skill_data = agent_data['skill_count'][skill]
        skill_data['count'] = skill_data.get('count', 0) + 1
        if success:
            skill_data['success'] = skill_data.get('success', 0) + 1
        else:
            skill_data['failure'] = skill_data.get('failure', 0) + 1
        skill_data['last_used'] = datetime.now().isoformat()
        
        # Track global skill usage
        if skill not in self.tracker['skill_usage']:
            self.tracker['skill_usage'][skill] = {
                'total_uses': 0,
                'success_count': 0,
                'failure_count': 0,
                'agents_using': []
            }
        
        skill_usage = self.tracker['skill_usage'][skill]
        skill_usage['total_uses'] = skill_usage.get('total_uses', 0) + 1
        if success:
            skill_usage['success_count'] = skill_usage.get('success_count', 0) + 1
        else:
            skill_usage['failure_count'] = skill_usage.get('failure_count', 0) + 1
        
        # Add agent to list if not already present
        if agent_id not in skill_usage.get('agents_using', []):
            if 'agents_using' not in skill_usage:
                skill_usage['agents_using'] = []
            skill_usage['agents_using'].append(agent_id)
        
        agent_data['last_activity'] = datetime.now().isoformat()
        
        # Add to history
        self.tracker['ability_history'].append({
            'agent_id': agent_id,
            'skill': skill,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        })
        
        # Keep only last 1000 history entries
        if len(self.tracker['ability_history']) > 1000:
            self.tracker['ability_history'] = self.tracker['ability_history'][-1000:]
        
        self.save_tracker()
    
    def get_agent_stats(self, agent_id: str) -> Dict:
        """Get statistics for an agent"""
        agent_data = self.tracker['agents'].get(agent_id, {})
        
        total = agent_data.get('total_executions', 0)
        successful = agent_data.get('successful_executions', 0)
        failed = agent_data.get('failed_executions', 0)
        
        success_rate = (successful / total * 100) if total > 0 else 0
        
        return {
            'agent_id': agent_id,
            'total_executions': total,
            'successful_executions': successful,
            'failed_executions': failed,
            'success_rate': round(success_rate, 2),
            'skill_count': agent_data.get('skill_count', {}),
            'last_activity': agent_data.get('last_activity'),
            'top_skills': self._get_top_skills(agent_data.get('skill_count', {}))
        }
    
    def _get_top_skills(self, skill_count: Dict, limit: int = 5) -> List[Dict]:
        """Get top skills by usage"""
        skills = []
        for skill, data in skill_count.items():
            skills.append({
                'skill': skill,
                'count': data.get('count', 0),
                'success': data.get('success', 0),
                'failure': data.get('failure', 0)
            })
        
        skills.sort(key=lambda x: x['count'], reverse=True)
        return skills[:limit]
    
    def get_skill_stats(self, skill: str) -> Dict:
        """Get statistics for a skill"""
        skill_usage = self.tracker['skill_usage'].get(skill, {})
        
        total = skill_usage.get('total_uses', 0)
        success = skill_usage.get('success_count', 0)
        failure = skill_usage.get('failure_count', 0)
        
        success_rate = (success / total * 100) if total > 0 else 0
        
        return {
            'skill': skill,
            'total_uses': total,
            'success_count': success,
            'failure_count': failure,
            'success_rate': round(success_rate, 2),
            'agents_using': skill_usage.get('agents_using', [])
        }
    
    def get_all_stats(self) -> Dict:
        """Get all statistics"""
        agents = {}
        for agent_id in self.tracker['agents']:
            agents[agent_id] = self.get_agent_stats(agent_id)
        
        skills = {}
        for skill in self.tracker['skill_usage']:
            skills[skill] = self.get_skill_stats(skill)
        
        return {
            'agents': agents,
            'skills': skills,
            'total_agents': len(agents),
            'total_skills_tracked': len(skills),
            'total_executions': sum(a.get('total_executions', 0) for a in agents.values()),
            'last_updated': self.tracker.get('last_updated')
        }
    
    def get_recent_activity(self, limit: int = 50) -> List[Dict]:
        """Get recent activity"""
        history = self.tracker.get('ability_history', [])
        return history[-limit:] if len(history) > limit else history
    
    def get_agent_activity(self, agent_id: str, limit: int = 50) -> List[Dict]:
        """Get recent activity for an agent"""
        history = self.tracker.get('ability_history', [])
        agent_history = [h for h in history if h.get('agent_id') == agent_id]
        return agent_history[-limit:] if len(agent_history) > limit else agent_history
    
    def get_skill_activity(self, skill: str, limit: int = 50) -> List[Dict]:
        """Get recent activity for a skill"""
        history = self.tracker.get('ability_history', [])
        skill_history = [h for h in history if h.get('skill') == skill]
        return skill_history[-limit:] if len(skill_history) > limit else skill_history
    
    def reset_agent_stats(self, agent_id: str):
        """Reset statistics for an agent"""
        if agent_id in self.tracker['agents']:
            self.tracker['agents'][agent_id] = {
                'skill_count': {},
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'last_activity': None
            }
            self.save_tracker()

# Global instance
agent_ability_tracker = AgentAbilityTracker()
