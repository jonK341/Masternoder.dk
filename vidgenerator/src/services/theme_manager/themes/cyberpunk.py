"""
Cyberpunk Theme Intelligence
Provides theme-specific intelligence and logic for Cyberpunk-themed videos
Neon aesthetics, tech, and dystopian elements
"""

from typing import Dict, Any, List, Optional


class CyberpunkThemeIntelligence:
    """Intelligence system for Cyberpunk theme"""
    
    def __init__(self):
        self.theme_name = 'cyberpunk'
        self.keywords = [
            'cyberpunk', 'neon', 'hacker', 'ai', 'dystopia', 'dystopian', 'future',
            'tech', 'technology', 'cyber', 'neural', 'matrix', 'virtual', 'reality',
            'augmented', 'cyborg', 'android', 'robot', 'synthetic', 'digital',
            'megacorp', 'corporation', 'corporate', 'underground', 'street',
            'noir', 'blade runner', 'ghost in the shell', 'neuromancer',
            'hack', 'cyber', 'net', 'data', 'code', 'program', 'virus',
            'neon lights', 'rain', 'night', 'city', 'urban', 'metropolis'
        ]
        self.color_palette = {
            'primary': ['#ff0080', '#ff00ff', '#ff6b9d'],  # Hot pink, magenta
            'secondary': ['#00ffff', '#00d4ff', '#00a8cc'],  # Cyan, electric blue
            'accent': ['#8000ff', '#b300ff', '#cc00ff'],  # Purple, violet
            'background': ['#0a0a0a', '#1a1a2e', '#16213e'],  # Dark backgrounds
            'neon': ['#ff0080', '#00ffff', '#ff00ff', '#8000ff']  # Neon colors
        }
        self.visual_elements = [
            'neon signs', 'holographic displays', 'cyber cityscapes',
            'rain-soaked streets', 'futuristic vehicles', 'neural interfaces',
            'data streams', 'code rain', 'holograms', 'augmented reality',
            'cyber implants', 'neon lights', 'dark alleys', 'corporate towers'
        ]
        self.music_styles = ['synthwave', 'electronic', 'dark ambient', 'cyberpunk']
    
    def analyze_content(self, prompt: str, title: str = None) -> Dict[str, Any]:
        """Analyze content for Cyberpunk theme relevance"""
        text = f"{title or ''} {prompt}".lower()
        
        # Count keyword matches
        matches = sum(1 for kw in self.keywords if kw in text)
        relevance_score = min(1.0, matches / len(self.keywords) * 4)
        
        # Detect specific cyberpunk elements
        detected_elements = []
        for element in self.visual_elements:
            if any(word in text for word in element.split()):
                detected_elements.append(element)
        
        # Detect color mentions
        color_mentions = []
        for color_group in self.color_palette.values():
            for color in color_group:
                if color.replace('#', '') in text or color in text:
                    color_mentions.append(color)
        
        # Detect tech keywords
        tech_keywords = ['ai', 'hack', 'cyber', 'neural', 'virtual', 'digital', 'code']
        tech_score = sum(1 for kw in tech_keywords if kw in text)
        
        return {
            'theme': self.theme_name,
            'relevance_score': relevance_score,
            'keyword_matches': matches,
            'detected_elements': detected_elements,
            'color_mentions': color_mentions,
            'tech_score': tech_score,
            'is_cyberpunk_content': relevance_score > 0.3
        }
    
    def get_theme_suggestions(self, intelligence: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get theme-specific suggestions based on intelligence"""
        suggestions = []
        
        # Suggest cyberpunk-specific visuals
        if intelligence.get('tech_score', 0) > 2:
            suggestions.append({
                'type': 'visual',
                'suggestion': 'Include holographic displays and data streams',
                'priority': 'high'
            })
        
        if intelligence.get('relevance_score', 0) > 0.5:
            suggestions.append({
                'type': 'visual',
                'suggestion': 'Use neon color palette (pink, cyan, purple)',
                'priority': 'high'
            })
        
        # Suggest music style
        suggestions.append({
            'type': 'audio',
            'suggestion': 'Synthwave or dark electronic music',
            'priority': 'medium'
        })
        
        # Suggest atmosphere
        suggestions.append({
            'type': 'atmosphere',
            'suggestion': 'Dark, rain-soaked urban environment',
            'priority': 'medium'
        })
        
        return suggestions
    
    def get_theme_config(self) -> Dict[str, Any]:
        """Get theme configuration"""
        return {
            'name': 'Cyberpunk',
            'description': 'Neon-lit dystopian future with advanced technology',
            'category': 'futuristic',
            'color_palette': self.color_palette,
            'visual_style': {
                'background': 'dark',
                'lighting': 'neon',
                'atmosphere': 'dystopian',
                'mood': 'dark',
                'contrast': 'high'
            },
            'audio_style': {
                'genre': 'synthwave',
                'tempo': 'moderate',
                'mood': 'dark',
                'instruments': ['synthesizer', 'electronic', 'bass']
            },
            'keywords': self.keywords,
            'intelligent': True
        }


def get_cyberpunk_theme(prompt: str = None, title: str = None) -> Dict[str, Any]:
    """Get Cyberpunk theme configuration"""
    intelligence = CyberpunkThemeIntelligence()
    
    config = intelligence.get_theme_config()
    
    if prompt or title:
        analysis = intelligence.analyze_content(prompt or '', title)
        config['analysis'] = analysis
        config['suggestions'] = intelligence.get_theme_suggestions(analysis)
    
    return config

