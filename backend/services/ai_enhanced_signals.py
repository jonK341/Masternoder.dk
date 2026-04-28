"""
AI-Enhanced Signal Collector
Adds AI intelligence to signal collection and processing
"""
from typing import Dict, List, Optional
from datetime import datetime
from backend.services.signal_collector import signal_collector
from backend.services.agent_ai_intelligence import agent_ai_intelligence


class AIEnhancedSignals:
    """AI-enhanced signal collection"""
    
    def __init__(self):
        self.collector = signal_collector
        self.ai = agent_ai_intelligence
    
    def intelligent_signal_processing(self, signal: Dict) -> Dict:
        """Process signal with AI intelligence"""
        # Use AI to understand signal context
        context = {
            'source': signal.get('source'),
            'signal_type': signal.get('signal_type'),
            'data': signal.get('data', {}),
            'timestamp': signal.get('timestamp')
        }
        
        understanding = self.ai.understand_context('signal_processor', context)
        
        # Predict signal importance
        prediction = self.ai.predict_outcome(
            agent_id='signal_analyzer',
            action={'type': 'process_signal', 'signal_id': signal.get('signal_id')},
            context=context
        )
        
        # Assess risk if applicable
        risk_assessment = None
        if 'error' in signal.get('signal_type', '').lower():
            risk_assessment = self.ai.assess_risk(
                agent_id='signal_risk_analyzer',
                scenario={
                    'signal_type': signal.get('signal_type'),
                    'data': signal.get('data', {})
                }
            )
        
        # Recognize patterns
        patterns = self.ai.recognize_pattern(
            agent_id='signal_pattern_recognizer',
            data=[signal],
            pattern_type='sequence'
        )
        
        # Make intelligent decision about signal handling
        options = [
            {'action': 'store', 'benefit': 0.8, 'cost': 0.1},
            {'action': 'alert', 'benefit': 0.6, 'cost': 0.3},
            {'action': 'ignore', 'benefit': 0.2, 'cost': 0.1}
        ]
        
        decision = self.ai.make_decision(
            agent_id='signal_handler',
            context=context,
            options=options,
            strategy='balanced'
        )
        
        return {
            'signal': signal,
            'understanding': understanding,
            'prediction': prediction,
            'risk_assessment': risk_assessment,
            'patterns': patterns,
            'decision': decision,
            'ai_recommendation': decision.get('decision', {}).get('action', 'store')
        }
    
    def intelligent_signal_pairing(self, signal1: Dict, signal2: Dict) -> Dict:
        """Intelligently pair signals using AI"""
        # Use AI to assess if signals should be paired
        context = {
            'signal1': signal1,
            'signal2': signal2,
            'similarity': self._calculate_similarity(signal1, signal2)
        }
        
        decision = self.ai.make_decision(
            agent_id='signal_pairer',
            context=context,
            options=[
                {'action': 'pair', 'benefit': 0.9, 'cost': 0.2},
                {'action': 'separate', 'benefit': 0.3, 'cost': 0.1}
            ],
            strategy='balanced'
        )
        
        return {
            'should_pair': decision.get('decision', {}).get('action') == 'pair',
            'confidence': decision.get('confidence', 0.5),
            'reasoning': decision.get('decision', {}).get('reasoning', '')
        }
    
    def predict_signal_trends(self, category: str, limit: int = 100) -> Dict:
        """Predict signal trends using AI"""
        signals = self.collector.get_signals(category=category, limit=limit)
        
        if not signals:
            return {'error': 'No signals found'}
        
        # Use AI to recognize trends
        patterns = self.ai.recognize_pattern(
            agent_id='signal_trend_analyzer',
            data=signals[-50:],  # Last 50 signals
            pattern_type='trend'
        )
        
        # Predict future signals
        prediction = self.ai.predict_outcome(
            agent_id='signal_predictor',
            action={'type': 'predict_trends', 'category': category},
            context={
                'signal_count': len(signals),
                'patterns': patterns.get('patterns', [])
            }
        )
        
        return {
            'category': category,
            'current_signals': len(signals),
            'patterns': patterns,
            'prediction': prediction,
            'trend_forecast': self._generate_trend_forecast(signals, patterns)
        }
    
    def _calculate_similarity(self, signal1: Dict, signal2: Dict) -> float:
        """Calculate similarity between signals"""
        # Simple similarity calculation
        type_match = 1.0 if signal1.get('signal_type') == signal2.get('signal_type') else 0.0
        source_match = 1.0 if signal1.get('source') == signal2.get('source') else 0.0
        
        return (type_match + source_match) / 2.0
    
    def _generate_trend_forecast(self, signals: List[Dict], patterns: Dict) -> str:
        """Generate trend forecast"""
        if not patterns.get('patterns'):
            return 'No clear trends detected'
        
        trend = patterns['patterns'][0].get('trend', 'stable')
        return f"Trend: {trend} - {patterns['patterns'][0].get('strength', 0):.2f} strength"


# Global instance
ai_enhanced_signals = AIEnhancedSignals()
