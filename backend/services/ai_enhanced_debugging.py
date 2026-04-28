"""
AI-Enhanced Debugging Service
Adds AI intelligence to debugging operations
"""
from typing import Dict, List, Optional
from datetime import datetime
from backend.services.debugging_database import debugging_database
from backend.services.agent_ai_intelligence import agent_ai_intelligence


class AIEnhancedDebugging:
    """AI-enhanced debugging service"""
    
    def __init__(self):
        self.db = debugging_database
        self.ai = agent_ai_intelligence
    
    def analyze_session(self, session_id: str) -> Dict:
        """Analyze debug session using AI"""
        session = self.db.get_session(session_id)
        if not session:
            return {'error': 'Session not found'}
        
        actions = self.db.get_session_actions(session_id)
        errors = self.db.get_session_errors(session_id)
        
        # Create context for AI analysis
        context = {
            'session_id': session_id,
            'actions_count': len(actions),
            'errors_count': len(errors),
            'duration': session.get('duration_seconds', 0),
            'status': session.get('status')
        }
        
        # Use AI to understand context
        understanding = self.ai.understand_context('debug_session_analyzer', context)
        
        # Analyze patterns
        patterns = self.ai.recognize_pattern(
            agent_id='debug_session_analyzer',
            data=actions[:50],  # Last 50 actions
            pattern_type='sequence'
        )
        
        # Assess risks
        risk_assessment = self.ai.assess_risk(
            agent_id='debug_session_analyzer',
            scenario={
                'errors_count': len(errors),
                'error_rate': len(errors) / max(len(actions), 1),
                'duration': session.get('duration_seconds', 0)
            }
        )
        
        # Generate insights
        insights = self._generate_insights(session, actions, errors)
        
        # Get recommendations
        recommendations = self._generate_recommendations(session, actions, errors)
        
        return {
            'session': session,
            'analysis': understanding,
            'patterns': patterns,
            'risk_assessment': risk_assessment,
            'insights': insights,
            'recommendations': recommendations,
            'ai_summary': self._generate_ai_summary(session, actions, errors)
        }
    
    def predict_error_likelihood(self, session_id: str, action_type: str) -> Dict:
        """Predict likelihood of error for an action"""
        session = self.db.get_session(session_id)
        actions = self.db.get_session_actions(session_id)
        errors = self.db.get_session_errors(session_id)
        
        # Use AI to predict
        prediction = self.ai.predict_outcome(
            agent_id='debug_error_predictor',
            action={'type': action_type, 'session_id': session_id},
            context={
                'previous_errors': len(errors),
                'error_rate': len(errors) / max(len(actions), 1),
                'session_duration': session.get('duration_seconds', 0) if session else 0
            }
        )
        
        return {
            'action_type': action_type,
            'prediction': prediction,
            'error_likelihood': prediction.get('prediction_score', 0.5),
            'recommendation': self._get_error_prevention_recommendation(prediction)
        }
    
    def suggest_optimizations(self, session_id: str) -> List[Dict]:
        """Suggest optimizations using AI"""
        session = self.db.get_session(session_id)
        actions = self.db.get_session_actions(session_id)
        
        # Use AI to develop optimization strategy
        strategy = self.ai.develop_strategy(
            agent_id='debug_optimizer',
            goal='optimize_debug_session',
            constraints={
                'session_id': session_id,
                'actions_count': len(actions)
            }
        )
        
        # Get AI recommendations
        optimizations = []
        for phase in strategy.get('phases', []):
            optimizations.append({
                'phase': phase.get('phase'),
                'action': phase.get('action'),
                'priority': phase.get('priority'),
                'ai_confidence': strategy.get('estimated_success', 0.7)
            })
        
        return optimizations
    
    def intelligent_error_resolution(self, error_id: str) -> Dict:
        """Use AI to suggest error resolution"""
        # Get error details (would need to add method to debugging_database)
        # For now, use AI to develop resolution strategy
        
        strategy = self.ai.develop_strategy(
            agent_id='error_resolver',
            goal='resolve_debug_error',
            constraints={'error_id': error_id}
        )
        
        # Use AI decision making
        resolution_options = [
            {'action': 'retry', 'benefit': 0.6, 'cost': 0.2},
            {'action': 'skip', 'benefit': 0.3, 'cost': 0.1},
            {'action': 'fix', 'benefit': 0.9, 'cost': 0.5}
        ]
        
        decision = self.ai.make_decision(
            agent_id='error_resolver',
            context={'error_id': error_id},
            options=resolution_options,
            strategy='balanced'
        )
        
        return {
            'error_id': error_id,
            'strategy': strategy,
            'recommended_action': decision.get('decision'),
            'confidence': decision.get('confidence', 0.5)
        }
    
    def _generate_insights(self, session: Dict, actions: List[Dict], errors: List[Dict]) -> List[str]:
        """Generate AI-powered insights"""
        insights = []
        
        # Calculate metrics
        error_rate = len(errors) / max(len(actions), 1)
        avg_action_time = sum(a.get('execution_time_ms', 0) for a in actions) / max(len(actions), 1)
        
        if error_rate > 0.3:
            insights.append('High error rate detected - consider reviewing error patterns')
        
        if avg_action_time > 1000:
            insights.append('Slow action execution - performance optimization recommended')
        
        # Use AI to recognize patterns
        if len(actions) > 10:
            patterns = self.ai.recognize_pattern(
                agent_id='debug_insight_generator',
                data=actions[-20:],
                pattern_type='sequence'
            )
            
            if patterns.get('patterns'):
                insights.append(f"Detected {len(patterns['patterns'])} action patterns")
        
        return insights
    
    def _generate_recommendations(self, session: Dict, actions: List[Dict], errors: List[Dict]) -> List[str]:
        """Generate AI-powered recommendations"""
        recommendations = []
        
        # Use AI to develop strategy
        strategy = self.ai.develop_strategy(
            agent_id='debug_recommender',
            goal='improve_debug_session',
            constraints={
                'errors': len(errors),
                'actions': len(actions)
            }
        )
        
        for phase in strategy.get('phases', []):
            recommendations.append(f"{phase.get('action')} (Priority: {phase.get('priority')})")
        
        return recommendations
    
    def _generate_ai_summary(self, session: Dict, actions: List[Dict], errors: List[Dict]) -> str:
        """Generate AI summary of session"""
        summary_parts = []
        
        summary_parts.append(f"Session {session.get('session_id', 'unknown')} analyzed")
        summary_parts.append(f"{len(actions)} actions performed")
        summary_parts.append(f"{len(errors)} errors encountered")
        
        if session.get('duration_seconds'):
            summary_parts.append(f"Duration: {session['duration_seconds']} seconds")
        
        # Use AI to understand and summarize
        context = {
            'actions': len(actions),
            'errors': len(errors),
            'duration': session.get('duration_seconds', 0)
        }
        
        understanding = self.ai.understand_context('debug_summarizer', context)
        
        return " | ".join(summary_parts)
    
    def _get_error_prevention_recommendation(self, prediction: Dict) -> str:
        """Get error prevention recommendation from AI prediction"""
        score = prediction.get('prediction_score', 0.5)
        
        if score > 0.7:
            return 'High error risk - implement additional error handling'
        elif score > 0.4:
            return 'Moderate error risk - monitor closely'
        else:
            return 'Low error risk - proceed with confidence'


# Global instance
ai_enhanced_debugging = AIEnhancedDebugging()
