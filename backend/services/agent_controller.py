"""
Agent Controller
Centralized controller for managing all agents
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentController:
    """Central controller for all agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'controller.json')
        self.load_data()
        self._initialize_agents()
    
    def load_data(self):
        """Load controller data"""
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
        """Default controller data"""
        return {
            'controller_id': 'agent_controller',
            'controller_name': 'Agent Controller',
            'version': '1.0.0',
            'agents_registered': [],
            'last_update': None,
            'total_agents': 0,
            'active_agents': 0,
            'settings': {
                'auto_start': True,
                'auto_restart': True,
                'health_check_interval': 300,
                'log_level': 'info'
            }
        }
    
    def save_data(self):
        """Save controller data"""
        try:
            self.data['last_update'] = datetime.now().isoformat()
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving controller data: {e}")
    
    def _initialize_agents(self):
        """Initialize all agent instances"""
        self.agents = {}
        
        # Core agents
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            self.agents['master_fix'] = master_fix_agent_skills
        except Exception as e:
            print(f"Warning: Could not load master_fix_agent: {e}")
        
        try:
            from backend.services.api_monitoring_agent import api_monitoring_agent
            self.agents['api_monitoring'] = api_monitoring_agent
        except Exception as e:
            print(f"Warning: Could not load api_monitoring_agent: {e}")
        
        # New specialized agents
        try:
            from backend.services.agent_content_generator import agent_content_generator
            self.agents['content_generator'] = agent_content_generator
        except Exception as e:
            print(f"Warning: Could not load content_generator: {e}")
        
        try:
            from backend.services.agent_battle_strategy import agent_battle_strategy
            self.agents['battle_strategy'] = agent_battle_strategy
        except Exception as e:
            print(f"Warning: Could not load battle_strategy: {e}")
        
        try:
            from backend.services.agent_social_engagement import agent_social_engagement
            self.agents['social_engagement'] = agent_social_engagement
        except Exception as e:
            print(f"Warning: Could not load social_engagement: {e}")
        
        try:
            from backend.services.agent_analytics import agent_analytics
            self.agents['analytics'] = agent_analytics
        except Exception as e:
            print(f"Warning: Could not load analytics: {e}")
        
        try:
            from backend.services.agent_security import agent_security
            self.agents['security'] = agent_security
        except Exception as e:
            print(f"Warning: Could not load security: {e}")
        
        try:
            from backend.services.agent_performance_optimizer import agent_performance_optimizer
            self.agents['performance_optimizer'] = agent_performance_optimizer
        except Exception as e:
            print(f"Warning: Could not load performance_optimizer: {e}")
        
        try:
            from backend.services.agent_user_experience import agent_user_experience
            self.agents['user_experience'] = agent_user_experience
        except Exception as e:
            print(f"Warning: Could not load user_experience: {e}")
        
        try:
            from backend.services.agent_integration import agent_integration
            self.agents['integration'] = agent_integration
        except Exception as e:
            print(f"Warning: Could not load integration: {e}")
        
        # System agents
        try:
            from backend.services.agent_automation import agent_automation
            self.agents['automation'] = agent_automation
        except Exception as e:
            print(f"Warning: Could not load automation: {e}")
        
        try:
            from backend.services.agent_activation_system import agent_activation_system
            self.agents['activation'] = agent_activation_system
        except Exception as e:
            print(f"Warning: Could not load activation: {e}")
        
        try:
            from backend.services.agent_research_tracker import agent_research_tracker
            self.agents['research'] = agent_research_tracker
        except Exception as e:
            print(f"Warning: Could not load research: {e}")
        
        try:
            from backend.services.agent_trigger_system import agent_trigger_system
            self.agents['trigger'] = agent_trigger_system
        except Exception as e:
            print(f"Warning: Could not load trigger: {e}")
        
        try:
            from backend.services.agent_support_service import agent_support_service
            self.agents['support'] = agent_support_service
        except Exception as e:
            print(f"Warning: Could not load support: {e}")
        
        try:
            from backend.services.agent_python_executor import agent_python_executor
            self.agents['python_executor'] = agent_python_executor
        except Exception as e:
            print(f"Warning: Could not load python_executor: {e}")
        
        # Manager and Secretary
        try:
            from backend.services.agent_manager import agent_manager
            self.agents['manager'] = agent_manager
        except Exception as e:
            print(f"Warning: Could not load manager: {e}")
        
        try:
            from backend.services.agent_secretary import agent_secretary
            self.agents['secretary'] = agent_secretary
        except Exception as e:
            print(f"Warning: Could not load secretary: {e}")
        
        # Agent Judge
        try:
            from backend.services.agent_judge import agent_judge
            self.agents['judge'] = agent_judge
        except Exception as e:
            print(f"Warning: Could not load judge: {e}")
        
        # Update registered agents
        self.data['agents_registered'] = list(self.agents.keys())
        self.data['total_agents'] = len(self.agents)
        self.save_data()
    
    def get_all_agents_status(self) -> Dict:
        """Get status of all agents"""
        status = {
            'controller': {
                'id': self.data['controller_id'],
                'name': self.data['controller_name'],
                'version': self.data['version'],
                'total_agents': len(self.agents),
                'last_update': self.data['last_update']
            },
            'agents': {}
        }
        
        active_count = 0
        for agent_id, agent in self.agents.items():
            try:
                if hasattr(agent, 'get_status'):
                    agent_status = agent.get_status()
                    status['agents'][agent_id] = {
                        'status': 'active',
                        'data': agent_status
                    }
                    active_count += 1
                else:
                    status['agents'][agent_id] = {
                        'status': 'unknown',
                        'error': 'No get_status method'
                    }
            except Exception as e:
                status['agents'][agent_id] = {
                    'status': 'error',
                    'error': str(e)
                }
        
        status['controller']['active_agents'] = active_count
        return status
    
    def execute_agent_skill(self, agent_id: str, skill_name: str, **kwargs) -> Dict:
        """Execute a skill on a specific agent"""
        if agent_id not in self.agents:
            return {'success': False, 'error': f'Agent {agent_id} not found'}
        
        agent = self.agents[agent_id]
        
        # Check if agent has the skill
        if hasattr(agent, skill_name):
            try:
                skill_method = getattr(agent, skill_name)
                result = skill_method(**kwargs)
                return {
                    'success': True,
                    'agent_id': agent_id,
                    'skill': skill_name,
                    'result': result
                }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e),
                    'agent_id': agent_id,
                    'skill': skill_name
                }
        else:
            return {
                'success': False,
                'error': f'Skill {skill_name} not found on agent {agent_id}',
                'agent_id': agent_id,
                'skill': skill_name
            }
    
    def get_agent_capabilities(self, agent_id: str) -> Dict:
        """Get capabilities of a specific agent"""
        if agent_id not in self.agents:
            return {'success': False, 'error': f'Agent {agent_id} not found'}
        
        agent = self.agents[agent_id]
        capabilities = {
            'agent_id': agent_id,
            'methods': [],
            'attributes': []
        }
        
        # Get all methods
        for attr_name in dir(agent):
            if not attr_name.startswith('_'):
                attr = getattr(agent, attr_name)
                if callable(attr):
                    capabilities['methods'].append(attr_name)
                else:
                    capabilities['attributes'].append(attr_name)
        
        return capabilities
    
    def calculate_with_agents(self, user_id: str = 'agent_user') -> Dict:
        """Execute calculator updates using agents - equal integration"""
        results = {
            'success': True,
            'user_id': user_id,
            'calculations': {},
            'errors': [],
            'points_awarded': {
                'xp': 0,
                'generation_points': 0,
                'battle_points': 0
            }
        }
        
        # Use master_fix_agent for calculator operations
        if 'master_fix' in self.agents:
            try:
                # Calculate with intelligence
                calc_result = self.execute_agent_skill(
                    'master_fix',
                    'skill_calculate_with_intelligence',
                    user_id=user_id
                )
                results['calculations']['intelligence'] = calc_result
                
                # Detect point loss
                loss_result = self.execute_agent_skill(
                    'master_fix',
                    'skill_detect_point_loss',
                    user_id=user_id
                )
                results['calculations']['loss_detection'] = loss_result
                
                # Get calculator statistics
                stats_result = self.execute_agent_skill(
                    'master_fix',
                    'skill_get_calculator_statistics',
                    user_id=user_id
                )
                results['calculations']['statistics'] = stats_result
                
                # Award points from calculations
                if calc_result.get('success') and 'result' in calc_result:
                    calc_data = calc_result.get('result', {})
                    if isinstance(calc_data, dict):
                        total_points = calc_data.get('total_points', 0)
                        if total_points > 0:
                            # Award points via trigger system
                            if 'trigger' in self.agents:
                                try:
                                    trigger_result = self.execute_agent_skill(
                                        'trigger',
                                        'award_points',
                                        trigger_id='calculator_update',
                                        user_id=user_id,
                                        metadata={'total_points': total_points}
                                    )
                                    if trigger_result.get('success'):
                                        points = trigger_result.get('result', {}).get('points_awarded', {})
                                        results['points_awarded']['xp'] += points.get('xp', 0)
                                        results['points_awarded']['generation_points'] += points.get('generation_points', 0)
                                        results['points_awarded']['battle_points'] += points.get('battle_points', 0)
                                except Exception as e:
                                    results['errors'].append(f'Points award: {e}')
                
            except Exception as e:
                results['errors'].append(f'Intelligence calculation: {e}')
        
        # Use analytics agent for analysis
        if 'analytics' in self.agents:
            try:
                analytics_result = self.execute_agent_skill(
                    'analytics',
                    'analyze_user_behavior',
                    user_id=user_id
                )
                results['calculations']['analytics'] = analytics_result
            except Exception as e:
                results['errors'].append(f'Analytics: {e}')
        
        # Use trigger system for points summary
        if 'trigger' in self.agents:
            try:
                trigger_stats = self.execute_agent_skill(
                    'trigger',
                    'get_trigger_stats'
                )
                results['calculations']['triggers'] = trigger_stats
            except Exception as e:
                results['errors'].append(f'Triggers: {e}')
        
        if results['errors']:
            results['success'] = False
        
        return results
    
    def get_status(self) -> Dict:
        """Get controller status"""
        return {
            'controller_id': self.data['controller_id'],
            'controller_name': self.data['controller_name'],
            'version': self.data['version'],
            'total_agents': len(self.agents),
            'active_agents': sum(1 for a in self.agents.values() if hasattr(a, 'get_status')),
            'agents_registered': self.data['agents_registered'],
            'last_update': self.data['last_update'],
            'settings': self.data['settings']
        }

# Global instance
agent_controller = AgentController()
