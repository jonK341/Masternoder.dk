"""
Teenager Likelihood Strategy Intelligence
AI system for understanding and predicting teenager behavior patterns
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)

class TeenagerStrategyIntelligence:
    """
    Teenager Likelihood Strategy Intelligence
    Analyzes patterns and predicts behavior
    """
    
    def __init__(self):
        self.behavior_patterns = {}
        self.likelihood_models = {}
        self.strategy_recommendations = {}
        self.age_groups = {
            'early_teen': (13, 15),
            'mid_teen': (16, 17),
            'late_teen': (18, 19)
        }
    
    def analyze_behavior_pattern(self, user_id: str, age: int, 
                                 behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze behavior pattern for teenager
        """
        age_group = self._get_age_group(age)
        
        pattern = {
            'user_id': user_id,
            'age': age,
            'age_group': age_group,
            'behavior_data': behavior_data,
            'analyzed_at': datetime.utcnow().isoformat(),
            'likelihood_scores': {},
            'strategy_recommendations': []
        }
        
        # Calculate likelihood scores
        pattern['likelihood_scores'] = self._calculate_likelihood_scores(age_group, behavior_data)
        
        # Generate strategy recommendations
        pattern['strategy_recommendations'] = self._generate_strategies(age_group, pattern['likelihood_scores'])
        
        if user_id not in self.behavior_patterns:
            self.behavior_patterns[user_id] = []
        
        self.behavior_patterns[user_id].append(pattern)
        
        return {'success': True, 'pattern': pattern}
    
    def _get_age_group(self, age: int) -> str:
        """Get age group for teenager"""
        if 13 <= age <= 15:
            return 'early_teen'
        elif 16 <= age <= 17:
            return 'mid_teen'
        elif 18 <= age <= 19:
            return 'late_teen'
        else:
            return 'unknown'
    
    def _calculate_likelihood_scores(self, age_group: str, 
                                    behavior_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Calculate likelihood scores for different behaviors
        """
        scores = {
            'social_engagement': 0.7,
            'content_creation': 0.6,
            'gaming_activity': 0.8,
            'learning_interest': 0.5,
            'peer_interaction': 0.9,
            'exploration_behavior': 0.7,
            'risk_taking': 0.4,
            'creativity': 0.6
        }
        
        # Adjust based on age group
        if age_group == 'early_teen':
            scores['social_engagement'] += 0.1
            scores['exploration_behavior'] += 0.1
        elif age_group == 'mid_teen':
            scores['content_creation'] += 0.2
            scores['peer_interaction'] += 0.1
        elif age_group == 'late_teen':
            scores['learning_interest'] += 0.2
            scores['creativity'] += 0.1
        
        # Normalize to 0-1
        for key in scores:
            scores[key] = min(max(scores[key], 0.0), 1.0)
        
        return scores
    
    def _generate_strategies(self, age_group: str, 
                            likelihood_scores: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Generate strategy recommendations
        """
        strategies = []
        
        # High social engagement -> encourage group activities
        if likelihood_scores.get('social_engagement', 0) > 0.7:
            strategies.append({
                'type': 'social',
                'recommendation': 'Encourage group activities and team challenges',
                'priority': 'high'
            })
        
        # High content creation -> provide creative tools
        if likelihood_scores.get('content_creation', 0) > 0.6:
            strategies.append({
                'type': 'creative',
                'recommendation': 'Provide advanced creative tools and templates',
                'priority': 'medium'
            })
        
        # High gaming activity -> gamify learning
        if likelihood_scores.get('gaming_activity', 0) > 0.7:
            strategies.append({
                'type': 'gamification',
                'recommendation': 'Gamify learning and skill development',
                'priority': 'high'
            })
        
        # High exploration -> provide discovery features
        if likelihood_scores.get('exploration_behavior', 0) > 0.6:
            strategies.append({
                'type': 'exploration',
                'recommendation': 'Enable exploration features and hidden content',
                'priority': 'medium'
            })
        
        return strategies
    
    def predict_likelihood(self, user_id: str, action_type: str) -> Dict[str, Any]:
        """
        Predict likelihood of user taking specific action
        """
        if user_id not in self.behavior_patterns:
            return {'success': False, 'error': 'No behavior data for user'}
        
        patterns = self.behavior_patterns[user_id]
        if not patterns:
            return {'success': False, 'error': 'No patterns found'}
        
        latest_pattern = patterns[-1]
        likelihood = latest_pattern['likelihood_scores'].get(action_type, 0.5)
        
        return {
            'success': True,
            'user_id': user_id,
            'action_type': action_type,
            'likelihood': likelihood,
            'confidence': 0.8,
            'recommendation': 'proceed' if likelihood > 0.6 else 'caution'
        }

# Global instance
teenager_strategy_intelligence = TeenagerStrategyIntelligence()

