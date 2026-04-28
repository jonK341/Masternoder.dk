"""
CEO Agent Service
Executive-level agent with strategic capabilities
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy import
def get_agent_ai_intelligence():
    from backend.services.agent_ai_intelligence import agent_ai_intelligence
    return agent_ai_intelligence


class CEOAgent:
    """CEO Agent with executive-level capabilities"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.ai = get_agent_ai_intelligence()
        self.profile_file = os.path.join(self.base_dir, 'logs', 'ceo_agent', 'profile.json')
        self.load_profile()
    
    def load_profile(self):
        """Load CEO agent profile"""
        os.makedirs(os.path.dirname(self.profile_file), exist_ok=True)
        
        if os.path.exists(self.profile_file):
            try:
                with open(self.profile_file, 'r') as f:
                    self.profile = json.load(f)
            except:
                self.profile = self._default_profile()
        else:
            self.profile = self._default_profile()
        
        self.save_profile()
    
    def _default_profile(self) -> Dict:
        """Default CEO agent profile"""
        return {
            'agent_id': 'ceo_agent',
            'class': 'executive',
            'level': 10,
            'power': 100,
            'status': 'active',
            'skills': {
                'strategic_planning': {'level': 10, 'power': 100, 'max_level': 10},
                'decision_making': {'level': 10, 'power': 100, 'max_level': 10},
                'leadership': {'level': 10, 'power': 100, 'max_level': 10},
                'innovation': {'level': 10, 'power': 100, 'max_level': 10},
                'financial_management': {'level': 10, 'power': 100, 'max_level': 10},
                'communication': {'level': 10, 'power': 100, 'max_level': 10},
                'problem_solving': {'level': 10, 'power': 100, 'max_level': 10},
                'performance_management': {'level': 10, 'power': 100, 'max_level': 10}
            },
            'limits': {
                'power_limit': 100,
                'actions_per_hour': 50,
                'strategic_decisions_per_day': 10,
                'communication_events_per_day': 20
            },
            'achievements': [],
            'statistics': {
                'decisions_made': 0,
                'strategies_developed': 0,
                'problems_solved': 0,
                'stakeholders_aligned': 0
            },
            'created_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat()
        }
    
    def save_profile(self):
        """Save CEO agent profile"""
        try:
            self.profile['last_updated'] = datetime.now().isoformat()
            with open(self.profile_file, 'w') as f:
                json.dump(self.profile, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving CEO profile: {e}")
    
    def strategic_planning(self, goal: str, timeframe: str = 'long-term', context: Dict = None) -> Dict:
        """Develop strategic plan"""
        try:
            # Use AI to develop strategy
            strategy = self.ai.develop_strategy(
                agent_id='ceo_agent',
                goal=goal,
                constraints={'timeframe': timeframe, **(context or {})}
            )
            
            # Update statistics
            self.profile['statistics']['strategies_developed'] += 1
            self.save_profile()
            
            return {
                'success': True,
                'goal': goal,
                'timeframe': timeframe,
                'strategy': strategy,
                'confidence': strategy.get('confidence', 0.8),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def make_executive_decision(self, options: List[Dict], context: Dict = None) -> Dict:
        """Make executive-level decision"""
        try:
            # Use AI to make decision
            decision = self.ai.make_decision(
                agent_id='ceo_agent',
                context=context or {},
                options=options,
                strategy='executive'
            )
            
            # Update statistics
            self.profile['statistics']['decisions_made'] += 1
            self.save_profile()
            
            return {
                'success': True,
                'decision': decision,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def assess_risk(self, action: Dict, context: Dict = None) -> Dict:
        """Assess risk for executive decisions"""
        try:
            risk = self.ai.assess_risk(
                agent_id='ceo_agent',
                action=action,
                context=context or {}
            )
            
            return {
                'success': True,
                'risk': risk,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def optimize_resources(self, resources: Dict, goals: List[str]) -> Dict:
        """Optimize resource allocation"""
        try:
            optimization = self.ai.optimize_system(
                agent_id='ceo_agent',
                system='resources',
                constraints={'resources': resources, 'goals': goals}
            )
            
            return {
                'success': True,
                'optimization': optimization,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_status(self) -> Dict:
        """Get CEO agent status"""
        return {
            'agent_id': self.profile['agent_id'],
            'class': self.profile['class'],
            'level': self.profile['level'],
            'power': self.profile['power'],
            'status': self.profile['status'],
            'skills': self.profile['skills'],
            'statistics': self.profile['statistics'],
            'limits': self.profile['limits']
        }


# Global instance
ceo_agent = CEOAgent()
