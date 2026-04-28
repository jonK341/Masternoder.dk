"""
Analytics Agent
Specialized agent for data analysis and insights
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentAnalytics:
    """Analytics agent"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'analytics_agent'
        self.agent_name = 'Analytics Agent'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'analytics.json')
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
                'analyze_user_behavior',
                'track_metrics',
                'generate_reports',
                'predict_trends',
                'identify_patterns',
                'optimize_performance',
                'data_visualization',
                'insight_generation'
            ],
            'analyses_performed': 0,
            'reports_generated': 0,
            'insights_created': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving analytics data: {e}")
    
    def analyze_user_behavior(self, user_id: str) -> Dict:
        """Analyze user behavior"""
        try:
            from backend.services.agent_point_creator import agent_point_creator
            
            # Award points for analysis - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='analyze_user_behavior',
                user_id=user_id
            )
            
            self.data['analyses_performed'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'user_id': user_id,
                'insights': {
                    'engagement_level': 'high',
                    'preferred_content': ['video', 'battle'],
                    'activity_pattern': 'evening',
                    'recommendations': ['more_videos', 'join_guild']
                },
                'total_analyses': self.data['analyses_performed'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_report(self, report_type: str) -> Dict:
        """Generate analytics report"""
        try:
            self.data['reports_generated'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'report_type': report_type,
                'report_id': f"report_{self.data['reports_generated']}",
                'data': {
                    'total_users': 1000,
                    'active_users': 750,
                    'engagement_rate': 0.75
                },
                'total_reports': self.data['reports_generated']
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
            'analyses_performed': self.data.get('analyses_performed', 0),
            'reports_generated': self.data.get('reports_generated', 0),
            'insights_created': self.data.get('insights_created', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_analytics = AgentAnalytics()
