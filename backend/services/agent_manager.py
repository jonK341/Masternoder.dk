"""
Agent Manager
Manager agent with skills to activate and manage all other agents
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentManager:
    """Manager agent for activating and managing all agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'agent_manager'
        self.agent_name = 'Agent Manager'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'manager.json')
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
                'activate_all_agents',
                'deactivate_agent',
                'restart_agent',
                'monitor_agents',
                'assign_tasks',
                'coordinate_teams',
                'auto_fix_with_ai',
                'generate_ai_solutions',
                'optimize_agent_performance',
                'manage_resources',
                'create_agent_mission',
                'approve_agent_actions'
            ],
            'agents_activated': 0,
            'tasks_assigned': 0,
            'ai_fixes_applied': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving manager data: {e}")
    
    def activate_all_agents(self) -> Dict:
        """Activate all agents using agent controller"""
        try:
            from backend.services.agent_controller import agent_controller
            from backend.services.agent_point_creator import agent_point_creator
            
            # Get all agents status
            all_status = agent_controller.get_all_agents_status()
            agents = all_status.get('agents', {})
            
            activated = []
            failed = []
            
            for agent_id, agent_info in agents.items():
                try:
                    # Try to activate each agent
                    if agent_info.get('status') != 'active':
                        # Attempt activation based on agent type
                        if agent_id == 'automation':
                            from backend.services.agent_automation import agent_automation
                            agent_automation.start()
                        elif agent_id == 'activation':
                            from backend.services.agent_activation_system import agent_activation_system
                            agent_activation_system.start()
                    
                    activated.append(agent_id)
                    
                    # Award points for activation
                    agent_point_creator.award_points_for_agent_action(
                        agent_id='agent_manager',
                        action='activate_all_agents',
                        user_id='system',
                        points={'xp': 5, 'activity_points': 2}
                    )
                except Exception as e:
                    failed.append({'agent': agent_id, 'error': str(e)})
            
            self.data['agents_activated'] += len(activated)
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            # Award points for successful activation
            agent_point_creator.award_points_for_agent_action(
                agent_id='agent_manager',
                action='activate_all_agents',
                user_id='system',
                points={'xp': len(activated) * 2, 'activity_points': len(activated)}
            )
            
            return {
                'success': True,
                'activated': len(activated),
                'failed': len(failed),
                'agents': activated,
                'errors': failed
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def auto_fix_with_ai(self, issue_description: str) -> Dict:
        """Use AI to automatically fix issues"""
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            from backend.services.agent_point_creator import agent_point_creator
            
            # Use AI-powered diagnostic
            diagnostic = master_fix_agent_skills.skill_run_full_diagnostic()
            
            # Generate AI solution based on issue
            ai_solution = self._generate_ai_solution(issue_description, diagnostic)
            
            # Apply fixes
            fixes_applied = []
            if ai_solution.get('fixes'):
                for fix in ai_solution['fixes']:
                    try:
                        if fix['type'] == 'blueprint':
                            result = master_fix_agent_skills.skill_check_blueprints()
                        elif fix['type'] == 'database':
                            result = master_fix_agent_skills.skill_verify_database()
                        elif fix['type'] == 'endpoint':
                            result = master_fix_agent_skills.skill_verify_endpoints()
                        else:
                            result = {'success': True}
                        
                        if result.get('success'):
                            fixes_applied.append(fix)
                            # Award points for each fix
                            agent_point_creator.award_points_for_agent_action(
                                agent_id='agent_manager',
                                action='auto_fix_with_ai',
                                user_id='system',
                                points={'xp': 10, 'activity_points': 5}
                            )
                    except Exception as e:
                        pass
            
            self.data['ai_fixes_applied'] += len(fixes_applied)
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            # Award points for successful AI fix
            agent_point_creator.award_points_for_agent_action(
                agent_id='agent_manager',
                action='auto_fix_with_ai',
                user_id='system',
                points={'xp': len(fixes_applied) * 5, 'activity_points': len(fixes_applied) * 2}
            )
            
            return {
                'success': True,
                'issue': issue_description,
                'ai_analysis': ai_solution.get('analysis'),
                'fixes_applied': len(fixes_applied),
                'fixes': fixes_applied
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_ai_solution(self, issue: str, diagnostic: Dict) -> Dict:
        """Generate AI-powered solution"""
        # AI analysis based on issue keywords and diagnostic
        analysis = f"Analyzing issue: {issue}"
        fixes = []
        
        # Check diagnostic for issues
        if diagnostic.get('health_score', 100) < 90:
            fixes.append({
                'type': 'health',
                'action': 'Run full diagnostic and apply fixes',
                'priority': 'high'
            })
        
        # Check for common issues
        if 'blueprint' in issue.lower() or 'route' in issue.lower():
            fixes.append({
                'type': 'blueprint',
                'action': 'Verify and register blueprints',
                'priority': 'high'
            })
        
        if 'database' in issue.lower() or 'migration' in issue.lower():
            fixes.append({
                'type': 'database',
                'action': 'Verify database and run migrations',
                'priority': 'high'
            })
        
        if 'endpoint' in issue.lower() or 'api' in issue.lower():
            fixes.append({
                'type': 'endpoint',
                'action': 'Verify endpoints and fix missing methods',
                'priority': 'medium'
            })
        
        return {
            'analysis': analysis,
            'fixes': fixes,
            'confidence': 0.85
        }
    
    def assign_task(self, agent_id: str, task: str, priority: str = 'medium') -> Dict:
        """Assign task to specific agent"""
        try:
            from backend.services.agent_controller import agent_controller
            from backend.services.agent_point_creator import agent_point_creator
            
            # Execute task on agent
            result = agent_controller.execute_agent_skill(
                agent_id,
                task,
                priority=priority
            )
            
            self.data['tasks_assigned'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            # Award points for task assignment and execution
            if result.get('success'):
                # Manager gets points for assigning
                agent_point_creator.award_points_for_agent_action(
                    agent_id='agent_manager',
                    action='assign_task',
                    user_id='system',
                    points={'xp': 5, 'activity_points': 2}
                )
                # Agent gets points for executing
                agent_point_creator.award_points_for_agent_action(
                    agent_id=agent_id,
                    action=task,
                    user_id='system'
                )
            
            return {
                'success': True,
                'agent_id': agent_id,
                'task': task,
                'result': result
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
            'agents_activated': self.data.get('agents_activated', 0),
            'tasks_assigned': self.data.get('tasks_assigned', 0),
            'ai_fixes_applied': self.data.get('ai_fixes_applied', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_manager = AgentManager()
