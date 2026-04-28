"""
Agent Secretary
Secretary agent with skills to coordinate, document, and support all agents
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentSecretary:
    """Secretary agent for coordination and documentation"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'agent_secretary'
        self.agent_name = 'Agent Secretary'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'secretary.json')
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
                'coordinate_meetings',
                'document_activities',
                'schedule_tasks',
                'track_progress',
                'generate_reports',
                'manage_communications',
                'organize_workflows',
                'assist_agents',
                'create_ai_documentation',
                'maintain_logs',
                'handle_requests',
                'optimize_schedules'
            ],
            'meetings_coordinated': 0,
            'reports_generated': 0,
            'tasks_scheduled': 0,
            'ai_docs_created': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving secretary data: {e}")
    
    def coordinate_agent_activation(self, user_id: str = 'agent_user') -> Dict:
        """Coordinate activation of all agents"""
        try:
            from backend.services.agent_manager import agent_manager
            from backend.services.agent_point_creator import agent_point_creator
            
            # Use manager to activate all agents
            result = agent_manager.activate_all_agents()
            
            # Document the activation
            self.document_activity('agent_activation', {
                'timestamp': datetime.now().isoformat(),
                'result': result
            })
            
            # Award points for coordination - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='coordinate_activation',
                user_id=user_id
            )
            
            self.data['meetings_coordinated'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'activation_result': result,
                'documented': True,
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def document_activity(self, activity_type: str, details: Dict) -> Dict:
        """Document agent activity"""
        try:
            log_file = os.path.join(self.base_dir, 'logs', 'agents', 'activity_log.json')
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            
            # Load existing log
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log = json.load(f)
            else:
                log = {'activities': []}
            
            # Add new activity
            activity = {
                'type': activity_type,
                'timestamp': datetime.now().isoformat(),
                'details': details
            }
            log['activities'].append(activity)
            
            # Keep only last 1000 activities
            if len(log['activities']) > 1000:
                log['activities'] = log['activities'][-1000:]
            
            # Save log
            with open(log_file, 'w') as f:
                json.dump(log, f, indent=2, default=str)
            
            return {'success': True, 'activity_logged': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_ai_report(self, report_type: str, user_id: str = 'agent_user') -> Dict:
        """Generate AI-powered report"""
        try:
            from backend.services.agent_controller import agent_controller
            from backend.services.agent_point_creator import agent_point_creator
            
            # Get all agents status
            all_status = agent_controller.get_all_agents_status()
            
            # Generate AI analysis
            ai_analysis = self._generate_ai_analysis(all_status, report_type)
            
            # Create report
            report = {
                'type': report_type,
                'timestamp': datetime.now().isoformat(),
                'summary': {
                    'total_agents': all_status['controller']['total_agents'],
                    'active_agents': all_status['controller']['active_agents'],
                    'health_score': ai_analysis.get('health_score', 0)
                },
                'ai_analysis': ai_analysis,
                'agents': all_status['agents']
            }
            
            # Save report
            report_file = os.path.join(self.base_dir, 'logs', 'agents', f'report_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            os.makedirs(os.path.dirname(report_file), exist_ok=True)
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Award points for report generation - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='generate_ai_report',
                user_id=user_id
            )
            
            self.data['reports_generated'] += 1
            self.data['ai_docs_created'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'report': report,
                'report_file': report_file,
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_ai_analysis(self, status: Dict, report_type: str) -> Dict:
        """Generate AI analysis of system status"""
        total_agents = status['controller']['total_agents']
        active_agents = status['controller']['active_agents']
        
        # Calculate health score
        health_score = (active_agents / total_agents * 100) if total_agents > 0 else 0
        
        # Analyze agent statuses
        issues = []
        recommendations = []
        
        for agent_id, agent_info in status['agents'].items():
            if agent_info.get('status') != 'active':
                issues.append(f"{agent_id} is not active")
                recommendations.append(f"Activate {agent_id}")
        
        if health_score < 80:
            recommendations.append("System health below optimal - run diagnostics")
        
        return {
            'health_score': health_score,
            'issues_found': len(issues),
            'issues': issues,
            'recommendations': recommendations,
            'analysis': f"System has {active_agents}/{total_agents} agents active. Health score: {health_score:.1f}%"
        }
    
    def schedule_auto_fix(self, schedule_type: str = 'daily') -> Dict:
        """Schedule automatic fixes"""
        try:
            from backend.services.agent_automation import agent_automation
            
            # Enable auto-fix in automation
            agent_automation.config['auto_fix_enabled'] = True
            agent_automation.save_config()
            
            # Schedule task
            task = {
                'name': 'auto_fix_daily',
                'enabled': True,
                'schedule': schedule_type,
                'action': 'auto_fix_with_ai',
                'created_at': datetime.now().isoformat()
            }
            
            self.data['tasks_scheduled'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'task_scheduled': task,
                'auto_fix_enabled': True
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
            'meetings_coordinated': self.data.get('meetings_coordinated', 0),
            'reports_generated': self.data.get('reports_generated', 0),
            'tasks_scheduled': self.data.get('tasks_scheduled', 0),
            'ai_docs_created': self.data.get('ai_docs_created', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_secretary = AgentSecretary()
