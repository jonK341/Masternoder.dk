"""
AI Content Generator - Generates scripts, prompts, and content using AI
"""
import os
from typing import Dict, Any, List, Optional


class AIContentGenerator:
    """Generates content using AI services"""
    
    def __init__(self):
        """Initialize AI content generator"""
        self.openai_api_key = os.getenv('OPENAI_API_KEY', '')
        self.openai_available = bool(self.openai_api_key)
    
    def generate_script(
        self,
        prompt: str,
        title: str,
        description: str = "",
        duration_minutes: int = 3,
        segments: int = 5
    ) -> Dict[str, Any]:
        """
        Generate documentary script using AI
        
        Args:
            prompt: Main topic/prompt
            title: Documentary title
            description: Additional description
            duration_minutes: Target duration in minutes
            segments: Number of segments/clips
        
        Returns:
            Dictionary with script, segments, etc.
        """
        if not self.openai_available:
            # Return placeholder script
            return self._generate_placeholder_script(prompt, title, segments)
        
        try:
            import openai
            
            system_prompt = """You are a professional documentary script writer. 
Create engaging, informative scripts for documentary videos. 
Break the script into segments suitable for video clips.
Each segment should be clear, concise, and visually descriptive."""
            
            user_prompt = f"""Create a documentary script about: {prompt}

Title: {title}
Description: {description}

Requirements:
- Duration: approximately {duration_minutes} minutes
- Break into {segments} segments
- Each segment should be suitable for a video clip (5-10 seconds each)
- Make it engaging and informative
- Use clear, descriptive language

Format the response as JSON with:
- "script": full script text
- "segments": array of segment objects, each with "text", "duration_seconds", and "description"
"""
            
            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON from response
            import json
            try:
                # Extract JSON if wrapped in markdown code blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                
                result = json.loads(content)
                return {
                    'success': True,
                    'script': result.get('script', content),
                    'segments': result.get('segments', []),
                    'provider': 'openai'
                }
            except json.JSONDecodeError:
                # If not JSON, treat entire response as script
                return {
                    'success': True,
                    'script': content,
                    'segments': self._split_into_segments(content, segments),
                    'provider': 'openai'
                }
                
        except Exception as e:
            print(f"[AIContentGenerator] Error generating script: {e}")
            return self._generate_placeholder_script(prompt, title, segments)
    
    def generate_video_prompts(
        self,
        script_segments: List[Dict[str, Any]],
        style: str = "documentary"
    ) -> List[str]:
        """
        Generate video generation prompts from script segments
        
        Args:
            script_segments: List of script segment dictionaries
            style: Visual style (documentary, cinematic, etc.)
        
        Returns:
            List of video prompts
        """
        prompts = []
        
        for i, segment in enumerate(script_segments):
            segment_text = segment.get('text', segment.get('description', ''))
            prompt = self.optimize_prompt(segment_text, style)
            prompts.append(prompt)
        
        return prompts
    
    def optimize_prompt(
        self,
        prompt: str,
        style: str = "documentary",
        quality_level: str = "high"
    ) -> str:
        """
        Optimize video generation prompt for better results
        
        Args:
            prompt: Original prompt text
            style: Visual style
            quality_level: Quality level (affects prompt detail)
        
        Returns:
            Optimized prompt
        """
        if not self.openai_available:
            # Basic optimization without AI
            style_prefixes = {
                'documentary': 'Professional documentary style, realistic, cinematic',
                'cinematic': 'Cinematic, film-like, dramatic lighting',
                'realistic': 'Photorealistic, high detail, natural lighting',
                'artistic': 'Artistic, creative, visually striking',
                'vibrant': 'Vibrant colors, dynamic, energetic',
                'wwii': 'Historical World War II documentary style, sepia tones, black and white, authentic 1940s period aesthetics, military green accents',
                'mtg': 'Fantasy card game aesthetic, magical elements, epic battles, mana effects, spells, creatures, planeswalkers, vibrant magical colors',
                'ctrl_a_delete': 'Tech cyberpunk theme, digital deletion, reset aesthetics, neon blue, matrix green, black, red, code visualization, hacking',
                'the_end': 'Apocalyptic end-of-world theme, dramatic visuals, dark red, orange, black, gray, destruction, final moments',
                'slaprygler': 'Intense discipline and punishment theme, dramatic action, dark red, black, gray, white, intense mood'
            }
            
            prefix = style_prefixes.get(style.lower(), 'Professional, high quality')
            return f"{prefix}, {prompt}"
        
        try:
            import openai
            
            optimization_prompt = f"""Optimize this video generation prompt for AI video generation:

Original prompt: {prompt}
Style: {style}
Quality level: {quality_level}

Create an optimized prompt that:
1. Is clear and specific
2. Includes visual details
3. Matches the {style} style
4. Is suitable for {quality_level} quality video generation
5. Is concise but descriptive

Return only the optimized prompt, no explanation."""

            client = openai.OpenAI(api_key=self.openai_api_key)
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are an expert at creating optimized prompts for AI video generation."},
                    {"role": "user", "content": optimization_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )
            
            optimized = response.choices[0].message.content.strip()
            return optimized if optimized else prompt
            
        except Exception as e:
            print(f"[AIContentGenerator] Error optimizing prompt: {e}")
            # Fallback to basic optimization
            style_prefixes = {
                'documentary': 'Professional documentary style, realistic, cinematic',
                'cinematic': 'Cinematic, film-like, dramatic lighting',
                'realistic': 'Photorealistic, high detail, natural lighting',
                'artistic': 'Artistic, creative, visually striking',
                'vibrant': 'Vibrant colors, dynamic, energetic',
                'wwii': 'Historical World War II documentary style, sepia tones, black and white, authentic 1940s period aesthetics, military green accents',
                'mtg': 'Fantasy card game aesthetic, magical elements, epic battles, mana effects, spells, creatures, planeswalkers, vibrant magical colors',
                'ctrl_a_delete': 'Tech cyberpunk theme, digital deletion, reset aesthetics, neon blue, matrix green, black, red, code visualization, hacking',
                'the_end': 'Apocalyptic end-of-world theme, dramatic visuals, dark red, orange, black, gray, destruction, final moments',
                'slaprygler': 'Intense discipline and punishment theme, dramatic action, dark red, black, gray, white, intense mood',
                'voldsrov': 'Intense battle theme with aggressive combat elements, crimson, dark red, black, orange, aggressive mood, combat-focused, Jons VoldsRøv ID = Ny §'
            }
            prefix = style_prefixes.get(style.lower(), 'Professional, high quality')
            return f"{prefix}, {prompt}"
    
    def ensure_style_consistency(
        self,
        segments: List[Dict[str, Any]],
        style: str = "documentary"
    ) -> List[Dict[str, Any]]:
        """
        Ensure visual style consistency across segments
        
        Args:
            segments: List of script segments
            style: Target visual style
        
        Returns:
            Segments with consistent style hints
        """
        # Add style hints to each segment
        for segment in segments:
            if 'style' not in segment:
                segment['style'] = style
            if 'visual_hints' not in segment:
                segment['visual_hints'] = self._get_style_hints(style)
        
        return segments
    
    def _get_style_hints(self, style: str) -> Dict[str, str]:
        """Get visual style hints for a style"""
        hints = {
            'documentary': {
                'lighting': 'natural, realistic',
                'color': 'balanced, authentic',
                'motion': 'smooth, steady',
                'composition': 'professional, well-framed'
            },
            'cinematic': {
                'lighting': 'dramatic, cinematic',
                'color': 'graded, film-like',
                'motion': 'cinematic, fluid',
                'composition': 'cinematic framing, rule of thirds'
            },
            'realistic': {
                'lighting': 'natural, daylight',
                'color': 'accurate, true-to-life',
                'motion': 'natural, realistic',
                'composition': 'natural, documentary-style'
            },
            'artistic': {
                'lighting': 'creative, artistic',
                'color': 'vibrant, stylized',
                'motion': 'dynamic, expressive',
                'composition': 'artistic, creative'
            },
            'wwii': {
                'lighting': 'period-appropriate, authentic 1940s',
                'color': 'sepia, black and white, military green',
                'motion': 'documentary-style, historical',
                'composition': 'period-accurate framing, authentic'
            },
            'mtg': {
                'lighting': 'magical, epic, fantasy',
                'color': 'magical blue, gold, purple, red',
                'motion': 'epic, dynamic, magical',
                'composition': 'fantasy art style, card game aesthetic'
            },
            'ctrl_a_delete': {
                'lighting': 'cyberpunk, neon, digital',
                'color': 'neon blue, matrix green, black, red',
                'motion': 'digital, glitchy, tech',
                'composition': 'cyberpunk, digital, code-like'
            },
            'the_end': {
                'lighting': 'dramatic, apocalyptic',
                'color': 'dark red, orange, black, gray',
                'motion': 'dramatic, final, intense',
                'composition': 'apocalyptic, end-of-world'
            },
            'slaprygler': {
                'lighting': 'intense, dramatic',
                'color': 'dark red, black, gray, white',
                'motion': 'intense, dramatic, action',
                'composition': 'dramatic, intense, action-focused'
            },
            'voldsrov': {
                'lighting': 'aggressive, combat',
                'color': 'crimson, dark red, black, orange',
                'motion': 'aggressive, combat, intense',
                'composition': 'combat-focused, aggressive, battle-ready'
            }
        }
        
        return hints.get(style.lower(), hints['documentary'])
    
    def _generate_placeholder_script(
        self,
        prompt: str,
        title: str,
        segments: int
    ) -> Dict[str, Any]:
        """Generate placeholder script when AI is not available"""
        script_parts = [
            f"Introduction to {title}",
            f"Exploring the topic of {prompt}",
            "Key insights and information",
            "Analysis and perspectives",
            f"Conclusion about {prompt}"
        ]
        
        segments_list = []
        for i, part in enumerate(script_parts[:segments]):
            segments_list.append({
                'text': f"Segment {i+1}: {part}",
                'duration_seconds': 5,
                'description': part
            })
        
        return {
            'success': True,
            'script': f"Documentary script about {prompt}",
            'segments': segments_list,
            'provider': 'placeholder'
        }
    
    def _split_into_segments(self, script: str, num_segments: int) -> List[Dict[str, Any]]:
        """Split script text into segments"""
        sentences = script.split('. ')
        segment_size = max(1, len(sentences) // num_segments)
        
        segments = []
        for i in range(num_segments):
            start_idx = i * segment_size
            end_idx = min((i + 1) * segment_size, len(sentences))
            
            if start_idx < len(sentences):
                segment_text = '. '.join(sentences[start_idx:end_idx])
                if segment_text and not segment_text.endswith('.'):
                    segment_text += '.'
                
                segments.append({
                    'text': segment_text,
                    'duration_seconds': 5,
                    'description': segment_text[:100]
                })
        
        return segments

