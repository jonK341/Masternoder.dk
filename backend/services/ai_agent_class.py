"""
AI Agent Class
New class of agents with AI skills and enhanced power
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy imports to avoid circular dependencies
def get_agent_ai_intelligence():
    from backend.services.agent_ai_intelligence import agent_ai_intelligence
    return agent_ai_intelligence

def get_unified_points_db():
    try:
        from backend.services.unified_points_database_enhanced import unified_points_db
        return unified_points_db
    except:
        return None


class AIAgent:
    """AI Agent class with enhanced capabilities and unified points integration"""
    
    def __init__(self, agent_id: str, base_dir: Optional[str] = None):
        self.agent_id = agent_id
        self.base_dir = base_dir or BASE_DIR
        self.ai = agent_ai_intelligence
        self.points_db = unified_points_db
        self.skills_file = os.path.join(self.base_dir, 'logs', 'ai_agents', f'{agent_id}_skills.json')
        self.limits_file = os.path.join(self.base_dir, 'logs', 'ai_agents', f'{agent_id}_limits.json')
        self.load_agent_data()
    
    def load_agent_data(self):
        """Load agent skills and limits"""
        os.makedirs(os.path.dirname(self.skills_file), exist_ok=True)
        
        if os.path.exists(self.skills_file):
            try:
                with open(self.skills_file, 'r') as f:
                    self.skills = json.load(f)
            except:
                self.skills = self._default_skills()
        else:
            self.skills = self._default_skills()
        
        if os.path.exists(self.limits_file):
            try:
                with open(self.limits_file, 'r') as f:
                    self.limits = json.load(f)
            except:
                self.limits = self._default_limits()
        else:
            self.limits = self._default_limits()
        
        self.save_agent_data()
    
    def _default_skills(self) -> Dict:
        """Default AI agent skills"""
        return {
            'ai_skills': {
                'decision_making': {'level': 1, 'max_level': 10, 'power': 10},
                'pattern_recognition': {'level': 1, 'max_level': 10, 'power': 10},
                'prediction': {'level': 1, 'max_level': 10, 'power': 10},
                'content_generation': {'level': 1, 'max_level': 10, 'power': 10},
                'optimization': {'level': 1, 'max_level': 10, 'power': 10},
                'learning': {'level': 1, 'max_level': 10, 'power': 10},
                'risk_assessment': {'level': 1, 'max_level': 10, 'power': 10},
                'strategy_development': {'level': 1, 'max_level': 10, 'power': 10}
            },
            'system_skills': {
                'debugging': {'level': 0, 'max_level': 10, 'power': 0},
                'monitoring': {'level': 0, 'max_level': 10, 'power': 0},
                'content_creation': {'level': 0, 'max_level': 10, 'power': 0},
                'data_analysis': {'level': 0, 'max_level': 10, 'power': 0},
                'automation': {'level': 0, 'max_level': 10, 'power': 0},
                'security': {'level': 0, 'max_level': 10, 'power': 0},
                'performance': {'level': 0, 'max_level': 10, 'power': 0},
                'integration': {'level': 0, 'max_level': 10, 'power': 0}
            },
            'bridged_skills': {},
            'skill_bridges': []
        }
    
    def _default_limits(self) -> Dict:
        """Default limits for AI agent"""
        return {
            'power_limit': 100,
            'action_limit_per_hour': 100,
            'content_generation_limit': 50,
            'decision_limit_per_minute': 60,
            'learning_rate_limit': 10,
            'skill_usage_limits': {
                'decision_making': 100,
                'pattern_recognition': 100,
                'prediction': 100,
                'content_generation': 50,
                'optimization': 50,
                'learning': 100,
                'risk_assessment': 100,
                'strategy_development': 50
            },
            'bridged_limits': {},
            'class_limits': {
                'ai_agent': {'power': 100, 'actions': 100},
                'debugging_agent': {'power': 50, 'actions': 50},
                'content_agent': {'power': 75, 'actions': 75},
                'monitoring_agent': {'power': 40, 'actions': 40}
            }
        }
    
    def save_agent_data(self):
        """Save agent skills and limits"""
        try:
            with open(self.skills_file, 'w') as f:
                json.dump(self.skills, f, indent=2, default=str)
            with open(self.limits_file, 'w') as f:
                json.dump(self.limits, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving agent data: {e}")
    
    def get_unified_points_context(self, user_id: str = 'system') -> Dict:
        """Get unified points system context for AI"""
        try:
            # Get points from all 178 systems
            points_context = {}
            
            # Get current point values
            try:
                from sqlalchemy import text
                from src.db.models import db
                
                results = db.session.execute(
                    text("""
                        SELECT system_name, point_value 
                        FROM system_point_snapshots 
                        WHERE user_id = :user_id
                        ORDER BY system_name
                    """),
                    {"user_id": user_id}
                ).fetchall()
                
                for row in results:
                    points_context[row[0]] = row[1]
            except Exception as e:
                print(f"Error getting points from database: {e}")
                # Fallback: return empty context
                points_context = {}
            
            # Get point statistics
            stats = {
                'total_systems': len(points_context),
                'total_points': sum(points_context.values()) if points_context else 0,
                'active_systems': len([v for v in points_context.values() if v > 0])
            }
            
            return {
                'points': points_context,
                'stats': stats,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting unified points context: {e}")
            return {'points': {}, 'stats': {'total_systems': 0, 'total_points': 0, 'active_systems': 0}, 'timestamp': datetime.now().isoformat()}
    
    def make_ai_decision(self, context: Dict, options: List[Dict], strategy: str = 'balanced') -> Dict:
        """Make AI decision with unified points context"""
        # Add unified points to context
        points_context = self.get_unified_points_context()
        enhanced_context = {
            **context,
            'unified_points': points_context,
            'points_available': points_context.get('stats', {}).get('total_points', 0)
        }
        
        # Check limits
        if not self._check_limits('decision_making'):
            return {'error': 'Decision limit reached', 'limit': self.limits['skill_usage_limits'].get('decision_making')}
        
        # Use AI to make decision
        decision = self.ai.make_decision(
            agent_id=self.agent_id,
            context=enhanced_context,
            options=options,
            strategy=strategy
        )
        
        # Update skill usage
        self._update_skill_usage('decision_making')
        
        # Award points for decision
        self._award_points_for_action('ai_decision', decision.get('confidence', 0.5))
        
        return decision
    
    def generate_content(self, content_type: str, parameters: Dict) -> Dict:
        """Generate content using AI"""
        # Check limits
        if not self._check_limits('content_generation'):
            return {'error': 'Content generation limit reached'}
        
        # Get unified points context
        points_context = self.get_unified_points_context()
        
        # Use AI content generator
        try:
            from backend.services.ai_content_generator import ai_content_generator
            content = ai_content_generator.generate_content(
                content_type=content_type,
                parameters=parameters,
                agent_class='ai_agent'
            )
        except Exception as e:
            print(f"Error using content generator: {e}")
            # Fallback to local generation
            if content_type == 'text':
                content = self._generate_text_content(parameters)
            elif content_type == 'code':
                content = self._generate_code_content(parameters)
            elif content_type == 'strategy':
                content = self._generate_strategy_content(parameters)
            else:
                content = {'error': f'Unknown content type: {content_type}'}
        
        # Update skill usage
        self._update_skill_usage('content_generation')
        
        # Award points
        self._award_points_for_action('content_generation', len(str(content).split()) / 100.0)
        
        return content
    
    def _generate_text_content(self, parameters: Dict) -> Dict:
        """Generate text content"""
        topic = parameters.get('topic', 'general')
        length = parameters.get('length', 100)
        
        # Use AI to develop strategy for content
        strategy = self.ai.develop_strategy(
            agent_id=self.agent_id,
            goal=f'generate_text_content_{topic}',
            constraints={'length': length}
        )
        
        return {
            'type': 'text',
            'topic': topic,
            'content': f"AI-generated content about {topic} (strategy: {strategy.get('strategy_id', 'unknown')})",
            'strategy': strategy,
            'length': length
        }
    
    def _generate_code_content(self, parameters: Dict) -> Dict:
        """Generate code content"""
        language = parameters.get('language', 'python')
        purpose = parameters.get('purpose', 'general')
        
        # Use AI to predict best approach
        prediction = self.ai.predict_outcome(
            agent_id=self.agent_id,
            action={'type': 'generate_code', 'language': language, 'purpose': purpose},
            context={'language': language, 'purpose': purpose}
        )
        
        return {
            'type': 'code',
            'language': language,
            'purpose': purpose,
            'code': f"# AI-generated {language} code for {purpose}\n# Prediction confidence: {prediction.get('confidence', 0.5):.2f}",
            'prediction': prediction
        }
    
    def _generate_strategy_content(self, parameters: Dict) -> Dict:
        """Generate strategy content"""
        goal = parameters.get('goal', 'optimize')
        
        strategy = self.ai.develop_strategy(
            agent_id=self.agent_id,
            goal=goal,
            constraints=parameters.get('constraints', {})
        )
        
        return {
            'type': 'strategy',
            'goal': goal,
            'strategy': strategy
        }
    
    def create_skill_bridge(self, skill1: str, skill2: str, bridge_type: str = 'complementary') -> Dict:
        """Create a bridge between two skills"""
        bridge_id = f"bridge_{skill1}_{skill2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        bridge = {
            'bridge_id': bridge_id,
            'skill1': skill1,
            'skill2': skill2,
            'bridge_type': bridge_type,
            'power_multiplier': 1.2 if bridge_type == 'complementary' else 1.0,
            'created_at': datetime.now().isoformat(),
            'usage_count': 0
        }
        
        if 'skill_bridges' not in self.skills:
            self.skills['skill_bridges'] = []
        self.skills['skill_bridges'].append(bridge)
        
        # Create bridged skill
        bridged_skill_name = f"{skill1}_{skill2}_bridged"
        self.skills['bridged_skills'][bridged_skill_name] = {
            'level': min(
                self.skills['ai_skills'].get(skill1, {}).get('level', 1),
                self.skills['ai_skills'].get(skill2, {}).get('level', 1)
            ),
            'max_level': 10,
            'power': (self.skills['ai_skills'].get(skill1, {}).get('power', 0) + 
                     self.skills['ai_skills'].get(skill2, {}).get('power', 0)) * bridge.get('power_multiplier', 1.0),
            'bridge_id': bridge_id
        }
        
        # Create bridged limit
        self.limits['bridged_limits'][bridged_skill_name] = {
            'limit': min(
                self.limits['skill_usage_limits'].get(skill1, 100),
                self.limits['skill_usage_limits'].get(skill2, 100)
            ) * 1.5,  # Bridged skills get 1.5x limit
            'usage': 0
        }
        
        self.save_agent_data()
        
        return bridge
    
    def _check_limits(self, skill_name: str) -> bool:
        """Check if skill usage is within limits"""
        limit = self.limits['skill_usage_limits'].get(skill_name, 100)
        # In real implementation, would track actual usage
        return True  # Simplified for now
    
    def _update_skill_usage(self, skill_name: str):
        """Update skill usage count"""
        # In real implementation, would track and update usage
        pass
    
    def _award_points_for_action(self, action_type: str, value: float):
        """Award unified points for AI action"""
        try:
            if self.points_db:
                points = {
                    'xp': int(value * 10),
                    'activity_points': int(value * 5)
                }
                
                self.points_db.add_points(
                    user_id='system',
                    point_type='xp',
                    amount=points['xp'],
                    source=f'ai_agent:{self.agent_id}:{action_type}',
                    metadata={'agent_id': self.agent_id, 'action': action_type}
                )
        except Exception as e:
            print(f"Error awarding points: {e}")
    
    def get_skill_definitions(self) -> Dict:
        """Get all skill definitions with empty spaces for missing skills"""
        definitions = {
            'ai_skills': {
                'decision_making': {
                    'name': 'Decision Making',
                    'description': 'Make intelligent decisions based on context',
                    'power_level': self.skills['ai_skills']['decision_making']['power'],
                    'limits': self.limits['skill_usage_limits'].get('decision_making', 100),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'decision_making' in [b['skill1'], b['skill2']]]
                },
                'pattern_recognition': {
                    'name': 'Pattern Recognition',
                    'description': 'Recognize patterns in data and behavior',
                    'power_level': self.skills['ai_skills']['pattern_recognition']['power'],
                    'limits': self.limits['skill_usage_limits'].get('pattern_recognition', 100),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'pattern_recognition' in [b['skill1'], b['skill2']]]
                },
                'prediction': {
                    'name': 'Prediction',
                    'description': 'Predict future outcomes and behaviors',
                    'power_level': self.skills['ai_skills']['prediction']['power'],
                    'limits': self.limits['skill_usage_limits'].get('prediction', 100),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'prediction' in [b['skill1'], b['skill2']]]
                },
                'content_generation': {
                    'name': 'Content Generation',
                    'description': 'Generate text, code, and strategic content',
                    'power_level': self.skills['ai_skills']['content_generation']['power'],
                    'limits': self.limits['skill_usage_limits'].get('content_generation', 50),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'content_generation' in [b['skill1'], b['skill2']]]
                },
                'optimization': {
                    'name': 'Optimization',
                    'description': 'Optimize systems and processes',
                    'power_level': self.skills['ai_skills']['optimization']['power'],
                    'limits': self.limits['skill_usage_limits'].get('optimization', 50),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'optimization' in [b['skill1'], b['skill2']]]
                },
                'learning': {
                    'name': 'Learning',
                    'description': 'Learn from experiences and improve',
                    'power_level': self.skills['ai_skills']['learning']['power'],
                    'limits': self.limits['skill_usage_limits'].get('learning', 100),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'learning' in [b['skill1'], b['skill2']]]
                },
                'risk_assessment': {
                    'name': 'Risk Assessment',
                    'description': 'Assess risks and provide recommendations',
                    'power_level': self.skills['ai_skills']['risk_assessment']['power'],
                    'limits': self.limits['skill_usage_limits'].get('risk_assessment', 100),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'risk_assessment' in [b['skill1'], b['skill2']]]
                },
                'strategy_development': {
                    'name': 'Strategy Development',
                    'description': 'Develop strategies to achieve goals',
                    'power_level': self.skills['ai_skills']['strategy_development']['power'],
                    'limits': self.limits['skill_usage_limits'].get('strategy_development', 50),
                    'bridges': [b for b in self.skills.get('skill_bridges', []) if 'strategy_development' in [b['skill1'], b['skill2']]]
                }
            },
            'system_skills': {
                'debugging': {'name': 'Debugging', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'monitoring': {'name': 'Monitoring', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'content_creation': {'name': 'Content Creation', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'data_analysis': {'name': 'Data Analysis', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'automation': {'name': 'Automation', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'security': {'name': 'Security', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'performance': {'name': 'Performance', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []},
                'integration': {'name': 'Integration', 'description': '', 'power_level': 0, 'limits': 0, 'bridges': []}
            },
            'bridged_skills': {},
            'missing_skills': self._identify_missing_skills()
        }
        
        # Add bridged skills
        for bridge in self.skills.get('skill_bridges', []):
            bridged_name = f"{bridge['skill1']}_{bridge['skill2']}_bridged"
            if bridged_name in self.skills.get('bridged_skills', {}):
                definitions['bridged_skills'][bridged_name] = {
                    'name': f"{bridge['skill1']} + {bridge['skill2']}",
                    'description': f"Bridged skill combining {bridge['skill1']} and {bridge['skill2']}",
                    'power_level': self.skills['bridged_skills'][bridged_name]['power'],
                    'limits': self.limits['bridged_limits'].get(bridged_name, {}).get('limit', 0),
                    'bridge': bridge
                }
        
        return definitions
    
    def _identify_missing_skills(self) -> List[Dict]:
        """Identify missing skills that should be added"""
        all_skills = set()
        
        # Collect all skill names
        for skill_type in ['ai_skills', 'system_skills']:
            all_skills.update(self.skills.get(skill_type, {}).keys())
        
        # Define expected skills
        expected_skills = {
            'ai_skills': ['decision_making', 'pattern_recognition', 'prediction', 'content_generation', 
                         'optimization', 'learning', 'risk_assessment', 'strategy_development',
                         'context_understanding', 'natural_language', 'image_processing', 'audio_processing'],
            'system_skills': ['debugging', 'monitoring', 'content_creation', 'data_analysis', 'automation',
                            'security', 'performance', 'integration', 'testing', 'deployment', 'scaling', 'maintenance']
        }
        
        missing = []
        for skill_type, skills in expected_skills.items():
            for skill in skills:
                if skill not in all_skills:
                    missing.append({
                        'skill_type': skill_type,
                        'skill_name': skill,
                        'status': 'missing',
                        'placeholder': True
                    })
        
        return missing
    
    def add_missing_skill(self, skill_type: str, skill_name: str, initial_level: int = 0) -> Dict:
        """Add a missing skill with placeholder"""
        if skill_type not in self.skills:
            self.skills[skill_type] = {}
        
        self.skills[skill_type][skill_name] = {
            'level': initial_level,
            'max_level': 10,
            'power': initial_level * 10
        }
        
        # Add limit
        if skill_name not in self.limits['skill_usage_limits']:
            self.limits['skill_usage_limits'][skill_name] = 100
        
        self.save_agent_data()
        
        return {
            'success': True,
            'skill_name': skill_name,
            'skill_type': skill_type,
            'level': initial_level
        }
    
    def get_class_limits(self, agent_class: str) -> Dict:
        """Get limits for a specific agent class"""
        return self.limits['class_limits'].get(agent_class, {
            'power': 50,
            'actions': 50
        })
    
    def set_class_limit(self, agent_class: str, power_limit: int, action_limit: int):
        """Set limits for an agent class"""
        if 'class_limits' not in self.limits:
            self.limits['class_limits'] = {}
        
        self.limits['class_limits'][agent_class] = {
            'power': power_limit,
            'actions': action_limit
        }
        
        self.save_agent_data()


# Global AI Agent instances
ai_agents = {}


def get_ai_agent(agent_id: str) -> AIAgent:
    """Get or create an AI agent"""
    if agent_id not in ai_agents:
        ai_agents[agent_id] = AIAgent(agent_id)
    return ai_agents[agent_id]
