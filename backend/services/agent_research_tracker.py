"""
Agent Research Tracker
Research and monitoring with comprehensive tracking
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentResearchTracker:
    """Research and monitoring tracker for agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.research_file = os.path.join(self.base_dir, 'logs', 'agent_research', 'research.json')
        self.monitoring_file = os.path.join(self.base_dir, 'logs', 'agent_research', 'monitoring.json')
        self.load_data()
    
    def load_data(self):
        """Load research and monitoring data"""
        os.makedirs(os.path.dirname(self.research_file), exist_ok=True)
        
        if os.path.exists(self.research_file):
            try:
                with open(self.research_file, 'r') as f:
                    self.research_data = json.load(f)
            except:
                self.research_data = self._default_research()
        else:
            self.research_data = self._default_research()
            self.save_research()
        
        if os.path.exists(self.monitoring_file):
            try:
                with open(self.monitoring_file, 'r') as f:
                    self.monitoring_data = json.load(f)
            except:
                self.monitoring_data = self._default_monitoring()
        else:
            self.monitoring_data = self._default_monitoring()
            self.save_monitoring()
    
    def _default_research(self) -> Dict:
        """Default research configuration"""
        return {
            'research_projects': [],
            'research_topics': [
                {
                    'id': 'api_structure',
                    'name': 'API Structure Research',
                    'description': 'Research API structure and patterns',
                    'status': 'active',
                    'priority': 'high'
                },
                {
                    'id': 'code_quality',
                    'name': 'Code Quality Research',
                    'description': 'Research code quality metrics',
                    'status': 'active',
                    'priority': 'medium'
                },
                {
                    'id': 'performance',
                    'name': 'Performance Research',
                    'description': 'Research system performance',
                    'status': 'active',
                    'priority': 'high'
                },
                {
                    'id': 'security',
                    'name': 'Security Research',
                    'description': 'Research security patterns',
                    'status': 'active',
                    'priority': 'high'
                },
                {
                    'id': 'point_systems',
                    'name': 'Point Systems Research',
                    'description': 'Research all 178 point systems',
                    'status': 'active',
                    'priority': 'high'
                },
                {
                    'id': 'trigger_optimization',
                    'name': 'Trigger Optimization Research',
                    'description': 'Research trigger system optimization',
                    'status': 'active',
                    'priority': 'medium'
                },
                {
                    'id': 'user_engagement',
                    'name': 'User Engagement Research',
                    'description': 'Research user engagement patterns',
                    'status': 'active',
                    'priority': 'high'
                },
                {
                    'id': 'economy_balance',
                    'name': 'Economy Balance Research',
                    'description': 'Research economy and trade balance',
                    'status': 'active',
                    'priority': 'medium'
                },
                {
                    'id': 'exploration_mechanics',
                    'name': 'Exploration Mechanics Research',
                    'description': 'Research exploration and discovery mechanics',
                    'status': 'active',
                    'priority': 'medium'
                },
                {
                    'id': 'education_systems',
                    'name': 'Education Systems Research',
                    'description': 'Research learning and education systems',
                    'status': 'active',
                    'priority': 'medium'
                },
                {
                    'id': 'event_systems',
                    'name': 'Event Systems Research',
                    'description': 'Research event and special occasion systems',
                    'status': 'active',
                    'priority': 'medium'
                },
                {
                    'id': 'customization_systems',
                    'name': 'Customization Systems Research',
                    'description': 'Research customization and personalization',
                    'status': 'active',
                    'priority': 'low'
                },
                {
                    'id': 'creativity_systems',
                    'name': 'Creativity Systems Research',
                    'description': 'Research creativity and innovation systems',
                    'status': 'active',
                    'priority': 'high'
                }
            ],
            'research_findings': [],
            'research_history': []
        }
    
    def _default_monitoring(self) -> Dict:
        """Default monitoring configuration"""
        return {
            'monitoring_targets': [
                {
                    'id': 'api_endpoints',
                    'name': 'API Endpoints',
                    'type': 'endpoint',
                    'status': 'active',
                    'metrics': ['response_time', 'error_rate', 'availability']
                },
                {
                    'id': 'database',
                    'name': 'Database',
                    'type': 'database',
                    'status': 'active',
                    'metrics': ['connection_count', 'query_time', 'table_size']
                },
                {
                    'id': 'system_resources',
                    'name': 'System Resources',
                    'type': 'system',
                    'status': 'active',
                    'metrics': ['cpu', 'memory', 'disk', 'network']
                },
                {
                    'id': 'agent_activity',
                    'name': 'Agent Activity',
                    'type': 'agent',
                    'status': 'active',
                    'metrics': ['skill_executions', 'tasks_completed', 'errors']
                },
                {
                    'id': 'point_systems',
                    'name': 'Point Systems',
                    'type': 'points',
                    'status': 'active',
                    'metrics': ['total_points', 'points_per_system', 'trigger_frequency']
                },
                {
                    'id': 'trigger_system',
                    'name': 'Trigger System',
                    'type': 'triggers',
                    'status': 'active',
                    'metrics': ['triggers_fired', 'points_awarded', 'trigger_success_rate']
                },
                {
                    'id': 'user_activity',
                    'name': 'User Activity',
                    'type': 'user',
                    'status': 'active',
                    'metrics': ['active_users', 'session_duration', 'engagement_rate']
                },
                {
                    'id': 'economy',
                    'name': 'Economy',
                    'type': 'economy',
                    'status': 'active',
                    'metrics': ['transactions', 'trade_volume', 'market_activity']
                },
                {
                    'id': 'exploration',
                    'name': 'Exploration',
                    'type': 'exploration',
                    'status': 'active',
                    'metrics': ['areas_explored', 'discoveries', 'unlocks']
                },
                {
                    'id': 'education',
                    'name': 'Education',
                    'type': 'education',
                    'status': 'active',
                    'metrics': ['courses_completed', 'knowledge_gained', 'certifications']
                },
                {
                    'id': 'events',
                    'name': 'Events',
                    'type': 'events',
                    'status': 'active',
                    'metrics': ['events_active', 'participation_rate', 'event_completions']
                },
                {
                    'id': 'customization',
                    'name': 'Customization',
                    'type': 'customization',
                    'status': 'active',
                    'metrics': ['customizations_applied', 'user_preferences', 'theme_usage']
                },
                {
                    'id': 'creativity',
                    'name': 'Creativity',
                    'type': 'creativity',
                    'status': 'active',
                    'metrics': ['creative_content', 'innovations', 'original_content']
                },
                {
                    'id': 'system_contributions',
                    'name': 'System Contributions',
                    'type': 'system',
                    'status': 'active',
                    'metrics': ['feedback_count', 'bug_reports', 'feature_requests']
                }
            ],
            'monitoring_data': [],
            'alerts': []
        }
    
    def save_research(self):
        """Save research data"""
        try:
            with open(self.research_file, 'w') as f:
                json.dump(self.research_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving research: {e}")
    
    def save_monitoring(self):
        """Save monitoring data"""
        try:
            with open(self.monitoring_file, 'w') as f:
                json.dump(self.monitoring_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving monitoring: {e}")
    
    def start_research(self, topic_id: str, agent_id: str = 'master_fix_agent') -> Dict:
        """Start a research project"""
        topic = next((t for t in self.research_data['research_topics'] if t.get('id') == topic_id), None)
        if not topic:
            return {'success': False, 'error': 'Research topic not found'}
        
        project = {
            'id': f"research_{len(self.research_data['research_projects']) + 1}",
            'topic_id': topic_id,
            'topic_name': topic['name'],
            'agent_id': agent_id,
            'status': 'in_progress',
            'started_at': datetime.now().isoformat(),
            'findings': [],
            'data_collected': []
        }
        
        self.research_data['research_projects'].append(project)
        self.save_research()
        
        return {
            'success': True,
            'project': project
        }
    
    def add_research_finding(self, project_id: str, finding: Dict) -> Dict:
        """Add a research finding"""
        project = next((p for p in self.research_data['research_projects'] if p.get('id') == project_id), None)
        if not project:
            return {'success': False, 'error': 'Research project not found'}
        
        finding['timestamp'] = datetime.now().isoformat()
        project['findings'].append(finding)
        self.research_data['research_findings'].append({
            'project_id': project_id,
            'finding': finding
        })
        self.save_research()
        
        return {
            'success': True,
            'finding': finding
        }
    
    def collect_monitoring_data(self, target_id: str, metrics: Dict) -> Dict:
        """Collect monitoring data"""
        target = next((t for t in self.monitoring_data['monitoring_targets'] if t.get('id') == target_id), None)
        if not target:
            return {'success': False, 'error': 'Monitoring target not found'}
        
        data_point = {
            'target_id': target_id,
            'target_name': target['name'],
            'timestamp': datetime.now().isoformat(),
            'metrics': metrics
        }
        
        self.monitoring_data['monitoring_data'].append(data_point)
        
        # Keep only last 1000 data points
        if len(self.monitoring_data['monitoring_data']) > 1000:
            self.monitoring_data['monitoring_data'] = self.monitoring_data['monitoring_data'][-1000:]
        
        self.save_monitoring()
        
        # Award points via trigger
        try:
            from backend.services.agent_trigger_system import agent_trigger_system
            agent_trigger_system.award_points('health_check', 'agent_user', {
                'target_id': target_id,
                'target_name': target['name']
            })
        except:
            pass
        
        return {
            'success': True,
            'data_point': data_point
        }
    
    def create_alert(self, target_id: str, alert_type: str, message: str, severity: str = 'medium') -> Dict:
        """Create a monitoring alert"""
        alert = {
            'id': f"alert_{len(self.monitoring_data['alerts']) + 1}",
            'target_id': target_id,
            'type': alert_type,
            'message': message,
            'severity': severity,
            'status': 'active',
            'created_at': datetime.now().isoformat(),
            'resolved_at': None
        }
        
        self.monitoring_data['alerts'].append(alert)
        self.save_monitoring()
        
        return {
            'success': True,
            'alert': alert
        }
    
    def get_research_summary(self) -> Dict:
        """Get research summary"""
        active_projects = [p for p in self.research_data['research_projects'] if p.get('status') == 'in_progress']
        completed_projects = [p for p in self.research_data['research_projects'] if p.get('status') == 'completed']
        
        return {
            'success': True,
            'active_projects': len(active_projects),
            'completed_projects': len(completed_projects),
            'total_findings': len(self.research_data['research_findings']),
            'topics': len(self.research_data['research_topics'])
        }
    
    def get_monitoring_summary(self) -> Dict:
        """Get monitoring summary"""
        active_alerts = [a for a in self.monitoring_data['alerts'] if a.get('status') == 'active']
        data_points = len(self.monitoring_data['monitoring_data'])
        
        return {
            'success': True,
            'monitoring_targets': len(self.monitoring_data['monitoring_targets']),
            'active_alerts': len(active_alerts),
            'data_points': data_points,
            'latest_data': self.monitoring_data['monitoring_data'][-10:] if data_points > 0 else []
        }

# Global instance
agent_research_tracker = AgentResearchTracker()
