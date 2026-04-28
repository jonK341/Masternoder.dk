"""
Agent Point Creator
Service for agents to create real value by awarding points for their activities
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentPointCreator:
    """Service for agents to award points and create value"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'point_creator.json')
        self.load_data()
    
    def load_data(self):
        """Load point creator data"""
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
        """Default data"""
        return {
            'total_points_awarded': {
                'xp': 0,
                'generation_points': 0,
                'battle_points': 0,
                'activity_points': 0,
                'social_points': 0
            },
            'points_by_agent': {},
            'points_by_action': {},
            'value_created': 0,
            'last_update': None
        }
    
    def save_data(self):
        """Save data"""
        try:
            self.data['last_update'] = datetime.now().isoformat()
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving point creator data: {e}")
    
    def award_points_for_agent_action(self, agent_id: str, action: str, user_id: str = 'agent_user', points: Optional[Dict] = None) -> Dict:
        """Award points for agent action - creates real value"""
        try:
            # Default points based on action type
            if points is None:
                points = self._calculate_points_for_action(action)
            
            # Award via trigger system
            from backend.services.agent_trigger_system import agent_trigger_system
            from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
            
            total_awarded = {
                'xp': 0,
                'generation_points': 0,
                'battle_points': 0,
                'activity_points': 0,
                'social_points': 0
            }
            
            # Award each point type
            for point_type, amount in points.items():
                if amount > 0:
                    # Use unified points trigger integration
                    result = unified_points_trigger_integration.award_points_with_trigger(
                        point_type=point_type,
                        user_id=user_id,
                        amount=amount,
                        metadata={
                            'agent_id': agent_id,
                            'action': action,
                            'source': 'agent_activity'
                        }
                    )
                    
                    if result.get('success'):
                        awarded = result.get('points_awarded', {})
                        total_awarded['xp'] += awarded.get('xp', 0)
                        total_awarded['generation_points'] += awarded.get('generation_points', 0)
                        total_awarded['battle_points'] += awarded.get('battle_points', 0)
                        total_awarded['activity_points'] += awarded.get('activity_points', 0)
                        total_awarded['social_points'] += awarded.get('social_points', 0)
            
            # Track points by agent
            if agent_id not in self.data['points_by_agent']:
                self.data['points_by_agent'][agent_id] = {
                    'total_points': 0,
                    'actions': 0,
                    'breakdown': {}
                }
            
            self.data['points_by_agent'][agent_id]['actions'] += 1
            for pt_type, amount in total_awarded.items():
                self.data['points_by_agent'][agent_id]['breakdown'][pt_type] = \
                    self.data['points_by_agent'][agent_id]['breakdown'].get(pt_type, 0) + amount
                self.data['points_by_agent'][agent_id]['total_points'] += amount
                self.data['total_points_awarded'][pt_type] += amount
            
            # Track by action
            if action not in self.data['points_by_action']:
                self.data['points_by_action'][action] = {
                    'count': 0,
                    'total_points': 0
                }
            self.data['points_by_action'][action]['count'] += 1
            self.data['points_by_action'][action]['total_points'] += sum(total_awarded.values())
            
            # Calculate value created
            self.data['value_created'] = sum(self.data['total_points_awarded'].values())
            self.save_data()
            
            return {
                'success': True,
                'agent_id': agent_id,
                'action': action,
                'user_id': user_id,
                'points_awarded': total_awarded,
                'total_value': sum(total_awarded.values())
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _calculate_points_for_action(self, action: str) -> Dict:
        """Calculate points based on action type"""
        # Base points for different action types
        action_points = {
            # Maintenance actions
            'check_blueprints': {'xp': 5, 'activity_points': 2},
            'verify_database': {'xp': 10, 'activity_points': 5},
            'check_file_integrity': {'xp': 8, 'activity_points': 3},
            'scan_missing_methods': {'xp': 15, 'activity_points': 5},
            'run_full_diagnostic': {'xp': 25, 'activity_points': 10},
            
            # Content actions
            'generate_content': {'xp': 20, 'generation_points': 15, 'activity_points': 5},
            'generate_video': {'xp': 30, 'generation_points': 25, 'activity_points': 10},
            'generate_clip': {'xp': 20, 'generation_points': 15, 'activity_points': 5},
            
            # Battle actions
            'create_strategy': {'xp': 15, 'battle_points': 20, 'activity_points': 5},
            'analyze_battle': {'xp': 10, 'battle_points': 15, 'activity_points': 3},
            
            # Social actions
            'coordinate_event': {'xp': 12, 'social_points': 18, 'activity_points': 5},
            'facilitate_discussion': {'xp': 8, 'social_points': 12, 'activity_points': 3},
            
            # Analysis actions
            'analyze_user_behavior': {'xp': 15, 'activity_points': 8},
            'generate_report': {'xp': 20, 'activity_points': 10},
            
            # Security actions
            'scan_vulnerabilities': {'xp': 25, 'activity_points': 10},
            'monitor_threats': {'xp': 15, 'activity_points': 5},
            
            # Performance actions
            'optimize_performance': {'xp': 20, 'activity_points': 10},
            'monitor_performance': {'xp': 10, 'activity_points': 5},
            
            # UX actions
            'analyze_ux': {'xp': 15, 'activity_points': 8},
            'gather_feedback': {'xp': 10, 'social_points': 5, 'activity_points': 5},
            
            # Integration actions
            'integrate_api': {'xp': 25, 'activity_points': 10},
            'sync_data': {'xp': 15, 'activity_points': 8},
            
            # Management actions
            'activate_all_agents': {'xp': 50, 'activity_points': 20},
            'auto_fix_with_ai': {'xp': 30, 'activity_points': 15},
            'assign_task': {'xp': 10, 'activity_points': 5},
            
            # Error migration tasks
            'accept_migration_task': {'xp': 10, 'activity_points': 5},
            'complete_migration_task': {'xp': 0, 'activity_points': 0},  # Points calculated dynamically
            'migrate_error_handlers': {'xp': 2, 'activity_points': 1},  # Per handler
            
            # Debugger tasks
            'accept_debugger_task': {'xp': 5, 'activity_points': 2},
            'complete_debugger_task': {'xp': 0, 'activity_points': 0},  # Points calculated dynamically
            
            # Secretary actions
            'coordinate_activation': {'xp': 20, 'activity_points': 10},
            'generate_ai_report': {'xp': 25, 'activity_points': 12},
            'document_activity': {'xp': 5, 'activity_points': 2},
            
            # Judge actions
            'judge_content_quality': {'xp': 20, 'activity_points': 10},
            'evaluate_agent_performance': {'xp': 25, 'activity_points': 12},
            'rate_system_health': {'xp': 30, 'activity_points': 15},
            
            # Default
            'skill_execution': {'xp': 5, 'activity_points': 2},
            'agent_activity': {'xp': 3, 'activity_points': 1}
        }
        
        return action_points.get(action, action_points['agent_activity'])
    
    def get_agent_value_created(self, agent_id: str) -> Dict:
        """Get value created by specific agent"""
        try:
            agent_data = self.data['points_by_agent'].get(agent_id, {})
            return {
                'success': True,
                'agent_id': agent_id,
                'total_points': agent_data.get('total_points', 0),
                'actions': agent_data.get('actions', 0),
                'breakdown': agent_data.get('breakdown', {}),
                'average_per_action': (
                    agent_data.get('total_points', 0) / agent_data.get('actions', 1)
                    if agent_data.get('actions', 0) > 0 else 0
                )
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_agents_value(self) -> Dict:
        """Get value created by all agents"""
        try:
            return {
                'success': True,
                'total_value_created': self.data['value_created'],
                'total_points_awarded': self.data['total_points_awarded'],
                'agents': self.data['points_by_agent'],
                'top_agents': sorted(
                    [
                        {
                            'agent_id': agent_id,
                            'total_points': data.get('total_points', 0),
                            'actions': data.get('actions', 0)
                        }
                        for agent_id, data in self.data['points_by_agent'].items()
                    ],
                    key=lambda x: x['total_points'],
                    reverse=True
                )[:10]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict:
        """Get point creator status"""
        return {
            'total_value_created': self.data['value_created'],
            'total_points_awarded': self.data['total_points_awarded'],
            'agents_count': len(self.data['points_by_agent']),
            'actions_tracked': len(self.data['points_by_action']),
            'last_update': self.data['last_update']
        }

# Global instance
agent_point_creator = AgentPointCreator()
