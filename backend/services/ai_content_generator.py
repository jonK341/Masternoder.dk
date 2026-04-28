"""
AI Content Generator
Generates content using AI with unified points integration
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Lazy imports
def get_agent_ai_intelligence():
    from backend.services.agent_ai_intelligence import agent_ai_intelligence
    return agent_ai_intelligence

def get_llm_service():
    from backend.services.llm_service import llm_service
    return llm_service

def get_unified_points_db():
    try:
        from backend.services.unified_points_database_enhanced import unified_points_db
        return unified_points_db
    except:
        return None


class AIContentGenerator:
    """AI-powered content generation with limits and unified points"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.ai = get_agent_ai_intelligence()
        self.points_db = get_unified_points_db()
        self.content_file = os.path.join(self.base_dir, 'logs', 'ai_content', 'generated_content.json')
        self.limits_file = os.path.join(self.base_dir, 'logs', 'ai_content', 'content_limits.json')
        self.load_data()
    
    def load_data(self):
        """Load content and limits data"""
        os.makedirs(os.path.dirname(self.content_file), exist_ok=True)
        
        if os.path.exists(self.content_file):
            try:
                with open(self.content_file, 'r') as f:
                    self.generated_content = json.load(f)
            except:
                self.generated_content = {'content': [], 'statistics': {}}
        else:
            self.generated_content = {'content': [], 'statistics': {}}
        
        if os.path.exists(self.limits_file):
            try:
                with open(self.limits_file, 'r') as f:
                    self.limits = json.load(f)
            except:
                self.limits = self._default_limits()
        else:
            self.limits = self._default_limits()
        
        self.save_data()
    
    def _default_limits(self) -> Dict:
        """Default content generation limits"""
        return {
            'daily_limits': {
                'text': 100,
                'code': 50,
                'strategy': 30,
                'image': 20,
                'video': 10,
                'audio': 20
            },
            'hourly_limits': {
                'text': 20,
                'code': 10,
                'strategy': 5,
                'image': 5,
                'video': 2,
                'audio': 5
            },
            'class_limits': {
                'ai_agent': {'daily': 100, 'hourly': 20},
                'content_agent': {'daily': 200, 'hourly': 40},
                'debugging_agent': {'daily': 20, 'hourly': 5},
                'system_agent': {'daily': 50, 'hourly': 10}
            },
            'usage_today': {},
            'usage_this_hour': {}
        }
    
    def save_data(self):
        """Save content and limits"""
        try:
            with open(self.content_file, 'w') as f:
                json.dump(self.generated_content, f, indent=2, default=str)
            with open(self.limits_file, 'w') as f:
                json.dump(self.limits, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving content data: {e}")
    
    def generate_content(self, content_type: str, parameters: Dict, agent_class: str = 'ai_agent') -> Dict:
        """Generate content with limits and unified points"""
        # Check limits
        if not self._check_limits(content_type, agent_class):
            return {
                'error': 'Content generation limit reached',
                'limit_type': self._get_limit_type(content_type, agent_class)
            }
        
        # Get unified points context
        points_context = self._get_unified_points_context()
        
        # Use AI to generate content
        content_context = {
            'content_type': content_type,
            'parameters': parameters,
            'unified_points': points_context,
            'agent_class': agent_class
        }
        
        # Generate based on type
        if content_type == 'text':
            content = self._generate_text(parameters, points_context)
        elif content_type == 'code':
            content = self._generate_code(parameters, points_context)
        elif content_type == 'strategy':
            content = self._generate_strategy(parameters, points_context)
        elif content_type == 'image':
            content = self._generate_image_description(parameters, points_context)
        elif content_type == 'video':
            content = self._generate_video_description(parameters, points_context)
        elif content_type == 'audio':
            content = self._generate_audio_description(parameters, points_context)
        else:
            content = {'error': f'Unknown content type: {content_type}'}
        
        # Record generation
        self._record_generation(content_type, agent_class)
        
        # Award points
        self._award_points_for_content(content_type, content)
        
        return content
    
    def _generate_text(self, parameters: Dict, points_context: Dict) -> Dict:
        """Generate text content - uses LLM when available, else fallback"""
        topic = parameters.get('topic', 'general')
        length = parameters.get('length', 100)
        style = parameters.get('style', 'informative')
        
        strategy = self.ai.develop_strategy(
            agent_id='content_generator',
            goal=f'generate_text_{topic}',
            constraints={'length': length, 'style': style, 'points_available': points_context.get('stats', {}).get('total_points', 0)}
        )
        
        understanding = self.ai.understand_context(
            agent_id='content_generator',
            context={'topic': topic, 'length': length, 'style': style}
        )
        
        content_text = None
        llm = get_llm_service()
        if llm.is_available():
            r = llm.complete(
                prompt=f"Write an informative piece about '{topic}'. Aim for approximately {length} words. Style: {style}. Be concise and engaging.",
                system_prompt="You are a content writer. Output only the article text, no meta-commentary.",
                temperature=0.7,
                max_tokens=min(4096, length * 2),
                task_type="default",
            )
            if r.success and r.content:
                content_text = f"# AI-Generated Content: {topic}\n\n{r.content.strip()}"
        
        if not content_text:
            content_text = f"""
# AI-Generated Content: {topic}

## Strategy
{strategy.get('strategy_id', 'unknown')}

## Content
This is AI-generated content about {topic}. The content is {length} words long and written in {style} style.

Points available in system: {points_context.get('stats', {}).get('total_points', 0)}
Active point systems: {points_context.get('stats', {}).get('active_systems', 0)}

## Key Points
- Generated using AI intelligence
- Context-aware content creation
- Integrated with unified points system
- Strategy-based generation
"""
        
        return {
            'type': 'text',
            'topic': topic,
            'content': content_text,
            'length': len(content_text.split()),
            'strategy': strategy,
            'understanding': understanding,
            'points_context': points_context
        }
    
    def _generate_code(self, parameters: Dict, points_context: Dict) -> Dict:
        """Generate code content - uses LLM when available, else fallback"""
        language = parameters.get('language', 'python')
        purpose = parameters.get('purpose', 'general')
        
        prediction = self.ai.predict_outcome(
            agent_id='code_generator',
            action={'type': 'generate_code', 'language': language, 'purpose': purpose},
            context={'language': language, 'purpose': purpose, 'points': points_context}
        )
        
        code = None
        llm = get_llm_service()
        if llm.is_available():
            r = llm.complete(
                prompt=f"Write {language} code for: {purpose}. Provide a working function or module. Include brief comments.",
                system_prompt="You are a helpful programmer. Output only valid code, no explanation.",
                temperature=0.3,
                max_tokens=1024,
                task_type="code",
            )
            if r.success and r.content:
                code = f"# AI-Generated {language} Code\n# Purpose: {purpose}\n\n{r.content.strip()}"
        
        if not code:
            code = f"""
# AI-Generated {language} Code
# Purpose: {purpose}
# Generated with AI intelligence
# Prediction confidence: {prediction.get('confidence', 0.5):.2f}

def ai_generated_function():
    \"\"\"
    AI-generated function for {purpose}
    Points context: {points_context.get('stats', {}).get('total_points', 0)} total points
    \"\"\"
    # Implementation would be generated here
    pass
"""
        
        return {
            'type': 'code',
            'language': language,
            'purpose': purpose,
            'code': code,
            'prediction': prediction,
            'points_context': points_context
        }
    
    def _generate_strategy(self, parameters: Dict, points_context: Dict) -> Dict:
        """Generate strategy content - uses LLM when available, else fallback"""
        goal = parameters.get('goal', 'optimize')
        constraints = parameters.get('constraints', {})
        
        strategy = self.ai.develop_strategy(
            agent_id='strategy_generator',
            goal=goal,
            constraints={
                **constraints,
                'points_available': points_context.get('stats', {}).get('total_points', 0)
            }
        )
        
        llm = get_llm_service()
        if llm.is_available():
            constraint_str = ", ".join(f"{k}={v}" for k, v in constraints.items()) if constraints else "none"
            r = llm.complete(
                prompt=f"Develop a clear strategy to achieve: {goal}. Constraints: {constraint_str}. List 3-5 actionable steps.",
                system_prompt="You are a strategic advisor. Be concise. Output numbered steps only.",
                temperature=0.5,
                max_tokens=512,
                task_type="reason",
            )
            if r.success and r.content:
                strategy['llm_strategy'] = r.content.strip()
                strategy['llm_enhanced'] = True
        
        return {
            'type': 'strategy',
            'goal': goal,
            'strategy': strategy,
            'points_context': points_context
        }
    
    def _generate_image_description(self, parameters: Dict, points_context: Dict) -> Dict:
        """Generate image description/content - uses LLM when available"""
        subject = parameters.get('subject', 'general')
        description = f"AI-generated image description for {subject}"
        used_llm = False
        
        llm = get_llm_service()
        if llm.is_available():
            r = llm.complete(
                prompt=f"Describe a compelling image/scene for: {subject}. 1-2 sentences, vivid and specific.",
                temperature=0.7,
                max_tokens=150,
                task_type="speed",
            )
            if r.success and r.content:
                description = r.content.strip()
                used_llm = True
        
        return {
            'type': 'image',
            'subject': subject,
            'description': description,
            'points_context': points_context,
            'placeholder': not used_llm
        }
    
    def _generate_video_description(self, parameters: Dict, points_context: Dict) -> Dict:
        """Generate video description/content - uses LLM when available"""
        topic = parameters.get('topic', 'general')
        description = f"AI-generated video description for {topic}"
        used_llm = False
        
        llm = get_llm_service()
        if llm.is_available():
            r = llm.complete(
                prompt=f"Describe a short video concept/scene for: {topic}. 1-2 sentences, visual and engaging.",
                temperature=0.7,
                max_tokens=150,
                task_type="speed",
            )
            if r.success and r.content:
                description = r.content.strip()
                used_llm = True
        
        return {
            'type': 'video',
            'topic': topic,
            'description': description,
            'points_context': points_context,
            'placeholder': not used_llm
        }
    
    def _generate_audio_description(self, parameters: Dict, points_context: Dict) -> Dict:
        """Generate audio description/content - uses LLM when available"""
        genre = parameters.get('genre', 'general')
        description = f"AI-generated audio description for {genre}"
        used_llm = False
        
        llm = get_llm_service()
        if llm.is_available():
            r = llm.complete(
                prompt=f"Describe an audio/sound design for: {genre}. 1-2 sentences, mood and elements.",
                temperature=0.7,
                max_tokens=150,
                task_type="speed",
            )
            if r.success and r.content:
                description = r.content.strip()
                used_llm = True
        
        return {
            'type': 'audio',
            'genre': genre,
            'description': description,
            'points_context': points_context,
            'placeholder': not used_llm
        }
    
    def _check_limits(self, content_type: str, agent_class: str) -> bool:
        """Check if content generation is within limits"""
        today = datetime.now().strftime('%Y%m%d')
        hour = datetime.now().strftime('%Y%m%d%H')
        
        # Get class limits
        class_limit = self.limits['class_limits'].get(agent_class, {'daily': 50, 'hourly': 10})
        
        # Check daily limit
        daily_key = f"{agent_class}_{today}"
        daily_usage = self.limits['usage_today'].get(daily_key, 0)
        if daily_usage >= class_limit['daily']:
            return False
        
        # Check hourly limit
        hourly_key = f"{agent_class}_{hour}"
        hourly_usage = self.limits['usage_this_hour'].get(hourly_key, 0)
        if hourly_usage >= class_limit['hourly']:
            return False
        
        return True
    
    def _get_limit_type(self, content_type: str, agent_class: str) -> str:
        """Get the type of limit that was reached"""
        today = datetime.now().strftime('%Y%m%d')
        hour = datetime.now().strftime('%Y%m%d%H')
        
        class_limit = self.limits['class_limits'].get(agent_class, {'daily': 50, 'hourly': 10})
        daily_key = f"{agent_class}_{today}"
        hourly_key = f"{agent_class}_{hour}"
        
        if self.limits['usage_today'].get(daily_key, 0) >= class_limit['daily']:
            return 'daily'
        elif self.limits['usage_this_hour'].get(hourly_key, 0) >= class_limit['hourly']:
            return 'hourly'
        return 'unknown'
    
    def _record_generation(self, content_type: str, agent_class: str):
        """Record content generation"""
        today = datetime.now().strftime('%Y%m%d')
        hour = datetime.now().strftime('%Y%m%d%H')
        
        daily_key = f"{agent_class}_{today}"
        hourly_key = f"{agent_class}_{hour}"
        
        self.limits['usage_today'][daily_key] = self.limits['usage_today'].get(daily_key, 0) + 1
        self.limits['usage_this_hour'][hourly_key] = self.limits['usage_this_hour'].get(hourly_key, 0) + 1
        
        # Update statistics
        if 'statistics' not in self.generated_content:
            self.generated_content['statistics'] = {}
        
        stat_key = f"{agent_class}_{content_type}"
        self.generated_content['statistics'][stat_key] = self.generated_content['statistics'].get(stat_key, 0) + 1
        
        self.save_data()
    
    def _get_unified_points_context(self, user_id: str = 'system') -> Dict:
        """Get unified points context"""
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
            
            points = {row[0]: row[1] for row in results}
            
            return {
                'points': points,
                'stats': {
                    'total_systems': len(points),
                    'total_points': sum(points.values()) if points else 0,
                    'active_systems': len([v for v in points.values() if v > 0])
                }
            }
        except Exception as e:
            print(f"Error getting unified points context: {e}")
            return {
                'points': {},
                'stats': {
                    'total_systems': 0,
                    'total_points': 0,
                    'active_systems': 0
                }
            }
    
    def _award_points_for_content(self, content_type: str, content: Dict):
        """Award unified points for content generation"""
        try:
            if self.points_db:
                # Calculate points based on content type and size
                base_points = {
                    'text': 10,
                    'code': 15,
                    'strategy': 20,
                    'image': 25,
                    'video': 30,
                    'audio': 20
                }
                
                points = base_points.get(content_type, 10)
                
                # Add size multiplier
                if 'length' in content:
                    points += int(content['length'] / 100)
                
                self.points_db.add_points(
                    user_id='system',
                    point_type='xp',
                    amount=points,
                    source=f'ai_content_generation:{content_type}',
                    metadata={'content_type': content_type, 'content_id': content.get('id')}
                )
        except Exception as e:
            print(f"Error awarding points for content: {e}")


# Global instance
ai_content_generator = AIContentGenerator()
