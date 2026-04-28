"""
Agent Judge
Judge agent with skills to evaluate, rate, and judge content, agents, and systems
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentJudge:
    """Judge agent for evaluation and rating"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'agent_judge'
        self.agent_name = 'Agent Judge'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'judge.json')
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
                'judge_content_quality',
                'evaluate_agent_performance',
                'rate_system_health',
                'assess_code_quality',
                'judge_user_behavior',
                'evaluate_competitions',
                'rate_achievements',
                'judge_creativity',
                'evaluate_efficiency',
                'assess_innovation',
                'judge_collaboration',
                'rate_overall_performance'
            ],
            'judgments_made': 0,
            'content_judged': 0,
            'agents_evaluated': 0,
            'systems_rated': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving judge data: {e}")
    
    def judge_content_quality(self, content_id: str, content_type: str, criteria: Optional[Dict] = None, user_id: str = 'agent_user') -> Dict:
        """Judge content quality"""
        try:
            from backend.services.agent_point_creator import agent_point_creator
            
            # Award points via trigger
            from backend.services.agent_trigger_system import agent_trigger_system
            agent_trigger_system.award_points('quality_evaluation', self.agent_id, {
                'content_id': content_id,
                'content_type': content_type
            })
            
            # Judge based on criteria
            criteria = criteria or {}
            quality_score = self._calculate_quality_score(criteria)
            
            judgment = {
                'content_id': content_id,
                'content_type': content_type,
                'quality_score': quality_score,
                'rating': self._score_to_rating(quality_score),
                'criteria_met': self._evaluate_criteria(criteria),
                'recommendations': self._generate_recommendations(quality_score, criteria),
                'judged_at': datetime.now().isoformat()
            }
            
            # Award points for judging - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='judge_content_quality',
                user_id=user_id
            )
            
            self.data['content_judged'] += 1
            self.data['judgments_made'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'judgment': judgment,
                'total_judged': self.data['content_judged'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def evaluate_agent_performance(self, agent_id: str, user_id: str = 'agent_user') -> Dict:
        """Evaluate agent performance"""
        try:
            from backend.services.agent_controller import agent_controller
            from backend.services.agent_point_creator import agent_point_creator
            
            # Get agent status
            agent_status = agent_controller.get_agent_capabilities(agent_id)
            all_status = agent_controller.get_all_agents_status()
            agent_info = all_status.get('agents', {}).get(agent_id, {})
            
            # Evaluate performance
            performance_score = self._calculate_performance_score(agent_info, agent_status)
            
            evaluation = {
                'agent_id': agent_id,
                'performance_score': performance_score,
                'rating': self._score_to_rating(performance_score),
                'capabilities': len(agent_status.get('methods', [])),
                'status': agent_info.get('status', 'unknown'),
                'recommendations': self._generate_agent_recommendations(performance_score, agent_info),
                'evaluated_at': datetime.now().isoformat()
            }
            
            # Award points for evaluation - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='evaluate_agent_performance',
                user_id=user_id
            )
            
            self.data['agents_evaluated'] += 1
            self.data['judgments_made'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'evaluation': evaluation,
                'total_evaluated': self.data['agents_evaluated'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def rate_system_health(self, user_id: str = 'agent_user') -> Dict:
        """Rate overall system health"""
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            from backend.services.agent_point_creator import agent_point_creator
            
            # Get system diagnostic
            diagnostic = master_fix_agent_skills.skill_run_full_diagnostic()
            health_score = diagnostic.get('health_score', 0)
            
            rating = {
                'health_score': health_score,
                'rating': self._score_to_rating(health_score),
                'components': diagnostic.get('components', {}),
                'issues': diagnostic.get('issues', []),
                'recommendations': self._generate_health_recommendations(health_score, diagnostic),
                'rated_at': datetime.now().isoformat()
            }
            
            # Award points for system rating - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action='rate_system_health',
                user_id=user_id
            )
            
            self.data['systems_rated'] += 1
            self.data['judgments_made'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'rating': rating,
                'total_rated': self.data['systems_rated'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _calculate_quality_score(self, criteria: Dict) -> float:
        """Calculate quality score from criteria"""
        score = 50.0  # Base score
        
        # Add points based on criteria
        if criteria.get('creativity', False):
            score += 15
        if criteria.get('innovation', False):
            score += 15
        if criteria.get('quality', False):
            score += 10
        if criteria.get('engagement', False):
            score += 10
        
        return min(100.0, score)
    
    def _calculate_performance_score(self, agent_info: Dict, agent_status: Dict) -> float:
        """Calculate agent performance score"""
        score = 50.0  # Base score
        
        if agent_info.get('status') == 'active':
            score += 30
        if len(agent_status.get('methods', [])) > 5:
            score += 10
        if len(agent_status.get('methods', [])) > 10:
            score += 10
        
        return min(100.0, score)
    
    def _score_to_rating(self, score: float) -> str:
        """Convert score to rating"""
        if score >= 90:
            return 'Excellent'
        elif score >= 75:
            return 'Good'
        elif score >= 60:
            return 'Fair'
        elif score >= 40:
            return 'Poor'
        else:
            return 'Critical'
    
    def _evaluate_criteria(self, criteria: Dict) -> List[str]:
        """Evaluate which criteria are met"""
        met = []
        if criteria.get('creativity'):
            met.append('Creativity')
        if criteria.get('innovation'):
            met.append('Innovation')
        if criteria.get('quality'):
            met.append('Quality')
        if criteria.get('engagement'):
            met.append('Engagement')
        return met
    
    def _generate_recommendations(self, score: float, criteria: Dict) -> List[str]:
        """Generate recommendations based on score"""
        recommendations = []
        if score < 60:
            recommendations.append('Improve overall quality')
        if not criteria.get('creativity'):
            recommendations.append('Add more creative elements')
        if not criteria.get('innovation'):
            recommendations.append('Introduce innovative features')
        return recommendations
    
    def _generate_agent_recommendations(self, score: float, agent_info: Dict) -> List[str]:
        """Generate agent recommendations"""
        recommendations = []
        if score < 70:
            recommendations.append('Improve agent performance')
        if agent_info.get('status') != 'active':
            recommendations.append('Activate agent')
        return recommendations
    
    def _generate_health_recommendations(self, score: float, diagnostic: Dict) -> List[str]:
        """Generate health recommendations"""
        recommendations = []
        if score < 80:
            recommendations.append('Run system maintenance')
        if diagnostic.get('issues'):
            recommendations.append('Address identified issues')
        return recommendations
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'level': self.data.get('level', 1),
            'experience': self.data.get('experience', 0),
            'judgments_made': self.data.get('judgments_made', 0),
            'content_judged': self.data.get('content_judged', 0),
            'agents_evaluated': self.data.get('agents_evaluated', 0),
            'systems_rated': self.data.get('systems_rated', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_judge = AgentJudge()
