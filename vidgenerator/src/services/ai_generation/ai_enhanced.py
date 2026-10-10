"""
Enhanced AI Generation System
Professional prompts, better context, improved fallbacks
"""
import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedAIGenerator:
    """Enhanced AI generation with professional prompts and context"""
    
    def __init__(self):
        self.providers = self._initialize_providers()
        self.prompt_templates = self._load_prompt_templates()
        self.context_enhancers = self._initialize_context_enhancers()
    
    def _initialize_providers(self):
        """Initialize AI providers"""
        try:
            from .ai_providers import AIProviderManager
            return AIProviderManager()
        except Exception as e:
            logger.error(f"Failed to initialize providers: {e}")
            return None
    
    def _load_prompt_templates(self) -> Dict[str, str]:
        """Load professional prompt templates"""
        return {
            'documentary': """Create a professional documentary video about: {topic}

Context:
- Theme: {theme}
- Style: {style}
- Duration: {duration} seconds
- Target Audience: {audience}

Requirements:
- Engaging narrative structure
- Professional pacing
- High-quality visuals
- Clear audio
- Smooth transitions
- Compelling storytelling

Additional Context:
{additional_context}

Generate a video that is informative, engaging, and professionally produced.""",
            
            'clip': """Create a short video clip: {description}

Context:
- Theme: {theme}
- Duration: {duration} seconds
- Style: {style}
- Mood: {mood}

Requirements:
- High visual quality
- Smooth motion
- Professional composition
- Engaging content
- Clear focus

Additional Context:
{additional_context}""",
            
            'intro': """Create an engaging video introduction: {topic}

Context:
- Theme: {theme}
- Duration: {duration} seconds
- Style: Professional and modern

Requirements:
- Attention-grabbing opening
- Clear message
- Professional quality
- Smooth transitions
- Engaging visuals""",
            
            'outro': """Create a professional video conclusion: {topic}

Context:
- Theme: {theme}
- Duration: {duration} seconds
- Style: Professional and memorable

Requirements:
- Strong closing
- Clear call-to-action
- Professional quality
- Memorable ending"""
        }
    
    def _initialize_context_enhancers(self) -> List:
        """Initialize context enhancement functions"""
        return [
            self._enhance_with_keywords,
            self._enhance_with_user_preferences,
            self._enhance_with_generation_history,
            self._enhance_with_performance_data
        ]
    
    def _enhance_with_keywords(self, context: Dict) -> Dict:
        """Enhance context with keyword intelligence"""
        try:
            keywords = context.get('intelligence', {}).get('sources', {}).get('keywords', {})
            if keywords and keywords.get('activeKeywords'):
                context['keyword_context'] = {
                    'keywords': keywords['activeKeywords'],
                    'categories': keywords.get('categories', {}),
                    'power_level': keywords.get('powerLevel', 0)
                }
        except Exception as e:
            logger.warning(f"Keyword enhancement failed: {e}")
        return context
    
    def _enhance_with_user_preferences(self, context: Dict) -> Dict:
        """Enhance context with user preferences"""
        try:
            user_data = context.get('intelligence', {}).get('sources', {}).get('context', {})
            if user_data and user_data.get('userPreferences'):
                context['user_preferences'] = user_data['userPreferences']
        except Exception as e:
            logger.warning(f"User preference enhancement failed: {e}")
        return context
    
    def _enhance_with_generation_history(self, context: Dict) -> Dict:
        """Enhance context with generation history"""
        try:
            history = context.get('intelligence', {}).get('sources', {}).get('context', {}).get('generationHistory', [])
            if history:
                context['generation_history'] = history[-5:]  # Last 5 generations
        except Exception as e:
            logger.warning(f"History enhancement failed: {e}")
        return context
    
    def _enhance_with_performance_data(self, context: Dict) -> Dict:
        """Enhance context with performance data"""
        try:
            perf = context.get('intelligence', {}).get('sources', {}).get('performance', {})
            if perf:
                context['performance_context'] = {
                    'load_time': perf.get('navigation', {}).get('loadComplete', 0),
                    'memory_usage': perf.get('memory', {}).get('usedJSHeapSize', 0) if perf.get('memory') else 0
                }
        except Exception as e:
            logger.warning(f"Performance enhancement failed: {e}")
        return context
    
    def build_enhanced_prompt(self, prompt_type: str, base_prompt: str, context: Dict) -> str:
        """Build enhanced prompt with all context"""
        # Enhance context
        enhanced_context = context.copy()
        for enhancer in self.context_enhancers:
            enhanced_context = enhancer(enhanced_context)
        
        # Get template
        template = self.prompt_templates.get(prompt_type, self.prompt_templates['documentary'])
        
        # Extract values from context
        theme = enhanced_context.get('theme', 'matrix')
        style = enhanced_context.get('style', 'professional')
        duration = enhanced_context.get('duration', 60)
        audience = enhanced_context.get('audience', 'general')
        
        # Build additional context string
        additional_context_parts = []
        
        if enhanced_context.get('keyword_context'):
            keywords = enhanced_context['keyword_context'].get('keywords', [])
            if keywords:
                additional_context_parts.append(f"Relevant Keywords: {', '.join([k.get('keyword', '') for k in keywords[:10]])}")
        
        if enhanced_context.get('user_preferences'):
            prefs = enhanced_context['user_preferences']
            if prefs.get('preferred_style'):
                additional_context_parts.append(f"User Preferred Style: {prefs['preferred_style']}")
        
        if enhanced_context.get('generation_history'):
            additional_context_parts.append(f"Previous Generations: {len(enhanced_context['generation_history'])}")
        
        additional_context = '\n'.join(additional_context_parts) if additional_context_parts else 'None'
        
        # Format prompt
        formatted_prompt = template.format(
            topic=base_prompt,
            theme=theme,
            style=style,
            duration=duration,
            audience=audience,
            additional_context=additional_context
        )
        
        return formatted_prompt
    
    async def generate_with_enhanced_context(
        self,
        prompt: str,
        prompt_type: str = 'documentary',
        context: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate with enhanced context and professional prompts"""
        try:
            # Build enhanced prompt
            enhanced_prompt = self.build_enhanced_prompt(prompt_type, prompt, context or {})
            
            logger.info(f"[Enhanced AI] Generated enhanced prompt (length: {len(enhanced_prompt)})")
            
            # Use provider manager if available
            if self.providers:
                result = await self.providers.generate_video(
                    prompt=enhanced_prompt,
                    **kwargs
                )
                
                # Add metadata
                result['metadata'] = {
                    'original_prompt': prompt,
                    'enhanced_prompt': enhanced_prompt,
                    'prompt_type': prompt_type,
                    'context_enhanced': True,
                    'timestamp': datetime.now().isoformat()
                }
                
                return result
            else:
                # Fallback
                return {
                    'success': False,
                    'error': 'No AI providers available',
                    'metadata': {
                        'original_prompt': prompt,
                        'enhanced_prompt': enhanced_prompt,
                        'prompt_type': prompt_type,
                        'context_enhanced': True
                    }
                }
        except Exception as e:
            logger.error(f"[Enhanced AI] Generation error: {e}")
            return {
                'success': False,
                'error': str(e),
                'metadata': {
                    'original_prompt': prompt,
                    'prompt_type': prompt_type
                }
            }
    
    def validate_generation_result(self, result: Dict) -> Dict[str, Any]:
        """Validate generation result"""
        validation = {
            'valid': False,
            'issues': [],
            'quality_score': 0.0
        }
        
        if not result.get('success'):
            validation['issues'].append('Generation failed')
            return validation
        
        # Check for video path
        if not result.get('video_path'):
            validation['issues'].append('No video path')
            return validation
        
        # Check file exists
        video_path = result['video_path']
        if not os.path.exists(video_path):
            validation['issues'].append('Video file does not exist')
            return validation
        
        # Check file size
        file_size = os.path.getsize(video_path)
        if file_size < 10240:  # Less than 10KB
            validation['issues'].append(f'Video file too small: {file_size} bytes')
            return validation
        
        # Calculate quality score
        quality_score = 0.0
        
        # Size score (0-0.3)
        if file_size > 1024 * 1024:  # > 1MB
            quality_score += 0.3
        elif file_size > 100 * 1024:  # > 100KB
            quality_score += 0.2
        else:
            quality_score += 0.1
        
        # Metadata score (0-0.3)
        if result.get('metadata'):
            quality_score += 0.3
        
        # Duration score (0-0.2)
        if result.get('duration') and result['duration'] > 0:
            quality_score += 0.2
        
        # Enhancement score (0-0.2)
        if result.get('metadata', {}).get('context_enhanced'):
            quality_score += 0.2
        
        validation['valid'] = True
        validation['quality_score'] = min(quality_score, 1.0)
        
        return validation

