"""
Intelligent Theme Selector
Automatically selects and applies themes based on content analysis
"""

from typing import Dict, Any, Optional, List
from .theme_config import ThemeConfig

# Try to import theme intelligences, but make them optional
try:
    from .themes.magic_gathering import MTGThemeIntelligence
except ImportError:
    MTGThemeIntelligence = None

try:
    from .themes.halo4 import Halo4ThemeIntelligence
except ImportError:
    Halo4ThemeIntelligence = None

try:
    from .themes.nazi import NaziThemeIntelligence
except ImportError:
    NaziThemeIntelligence = None

try:
    from .themes.cyberpunk import CyberpunkThemeIntelligence
except ImportError:
    CyberpunkThemeIntelligence = None


class IntelligentThemeSelector:
    """Intelligent theme selection based on content analysis"""
    
    def __init__(self):
        self.theme_intelligences = {
            'mtg': MTGThemeIntelligence() if MTGThemeIntelligence else None,
            'halo4': Halo4ThemeIntelligence() if Halo4ThemeIntelligence else None,
            'nazi_wwii': NaziThemeIntelligence() if NaziThemeIntelligence else None,
            'cyberpunk': CyberpunkThemeIntelligence() if CyberpunkThemeIntelligence else None
        }
        
        self.theme_keywords = {
            'mtg': ['magic', 'gathering', 'mtg', 'mana', 'planeswalker', 'card', 'spell', 'creature', 'artifact', 'enchantment'],
            'halo4': ['halo', 'spartan', 'master chief', 'covenant', 'forerunner', 'unsc', 'requiem', 'promethean'],
            'nazi_wwii': ['nazi', 'wwii', 'world war', 'hitler', 'germany', 'nuremberg', 'holocaust', 'blitzkrieg', 'stalingrad', 'normandy'],
            'cyberpunk': ['cyberpunk', 'neon', 'hacker', 'ai', 'dystopia', 'cyber', 'neural', 'virtual', 'cyborg', 'android', 'blade runner', 'ghost in the shell'],
            'matrix': ['matrix', 'neo', 'morpheus', 'trinity', 'agent smith', 'red pill', 'blue pill', 'code rain']
        }
    
    def detect_theme_from_content(self, prompt: str, title: str = None) -> str:
        """Automatically detect theme from content"""
        text = f"{title or ''} {prompt}".lower()
        
        # Count keyword matches for each theme
        theme_scores = {}
        for theme, keywords in self.theme_keywords.items():
            score = sum(1 for kw in keywords if kw in text)
            if score > 0:
                theme_scores[theme] = score
        
        # Return theme with highest score, or default to matrix
        if theme_scores:
            best_theme = max(theme_scores.items(), key=lambda x: x[1])[0]
            return best_theme
        
        return 'matrix'  # Default theme
    
    def get_intelligent_theme(self, prompt: str, title: str = None, preferred_theme: str = None) -> Dict[str, Any]:
        """Get intelligent theme configuration based on content"""
        # Use preferred theme if provided, otherwise auto-detect
        theme_name = preferred_theme or self.detect_theme_from_content(prompt, title)
        
        # Get theme with intelligence
        theme_config = ThemeConfig.get_theme(theme_name, prompt, title)
        
        return {
            'theme': theme_name,
            'config': theme_config,
            'auto_detected': preferred_theme is None,
            'confidence': self._calculate_confidence(prompt, title, theme_name)
        }
    
    def _calculate_confidence(self, prompt: str, title: str, theme: str) -> float:
        """Calculate confidence score for theme detection"""
        text = f"{title or ''} {prompt}".lower()
        keywords = self.theme_keywords.get(theme, [])
        
        if not keywords:
            return 0.5  # Default confidence
        
        matches = sum(1 for kw in keywords if kw in text)
        max_possible = len(keywords)
        
        if max_possible == 0:
            return 0.5
        
        confidence = min(1.0, matches / max_possible * 2)  # Scale up for better detection
        return confidence
    
    def list_available_themes(self) -> List[Dict[str, Any]]:
        """List all available themes with descriptions"""
        themes = []
        for theme_id, theme_config in ThemeConfig.THEMES.items():
            themes.append({
                'id': theme_id,
                'name': theme_config.get('name', theme_id),
                'description': theme_config.get('description', ''),
                'intelligent': theme_config.get('intelligent', False),
                'category': theme_config.get('category', 'general')
            })
        return themes


def select_theme_for_generation(prompt: str, title: str = None, user_preference: str = None) -> Dict[str, Any]:
    """Select theme for video generation with intelligence"""
    selector = IntelligentThemeSelector()
    return selector.get_intelligent_theme(prompt, title, user_preference)

