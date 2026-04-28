"""
Battle Strategy Agent
Specialized agent for battle strategies and tactics
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentBattleStrategy:
    """Battle strategy agent"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'battle_strategy_agent'
        self.agent_name = 'Battle Strategy Agent'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'battle_strategy.json')
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
                'analyze_battle',
                'create_strategy',
                'predict_outcome',
                'optimize_tactics',
                'team_coordination',
                'defense_planning',
                'offense_planning',
                'counter_strategy'
            ],
            'battles_analyzed': 0,
            'strategies_created': 0,
            'victories': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving battle strategy data: {e}")
    
    def create_strategy(self, battle_type: str, parameters: Dict, user_id: str = 'agent_user') -> Dict:
        """Create battle strategy"""
        try:
            from backend.services.agent_point_creator import agent_point_creator
            
            # Award points via trigger
            from backend.services.agent_trigger_system import agent_trigger_system
            trigger_map = {
                'pvp': 'pvp_battle',
                'pve': 'pve_battle',
                'team': 'team_battle',
                'guild': 'guild_battle',
                'arena': 'arena_battle'
            }
            trigger_id = trigger_map.get(battle_type, 'skill_execution')
            agent_trigger_system.award_points(trigger_id, self.agent_id, {
                'battle_type': battle_type,
                'parameters': parameters
            })
            
            # Award points for strategy creation - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='create_strategy',
                user_id=user_id
            )
            
            self.data['strategies_created'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'battle_type': battle_type,
                'strategy': {
                    'offense': 'balanced',
                    'defense': 'moderate',
                    'tactics': ['combo', 'ultimate']
                },
                'total_strategies': self.data['strategies_created'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def analyze_battle(self, battle_id: str) -> Dict:
        """Analyze battle"""
        try:
            self.data['battles_analyzed'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'battle_id': battle_id,
                'analysis': {
                    'strengths': ['offense', 'speed'],
                    'weaknesses': ['defense'],
                    'recommendations': ['improve_defense', 'use_tactics']
                },
                'total_analyzed': self.data['battles_analyzed']
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
            'battles_analyzed': self.data.get('battles_analyzed', 0),
            'strategies_created': self.data.get('strategies_created', 0),
            'victories': self.data.get('victories', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_battle_strategy = AgentBattleStrategy()
