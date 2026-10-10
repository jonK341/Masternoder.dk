"""Theme Configuration System with Intelligence"""
from typing import Dict, Any, Optional
from pathlib import Path
import os

# Import intelligent theme systems
try:
    from .themes.magic_gathering import get_mtg_theme, MTGThemeIntelligence
except ImportError:
    get_mtg_theme = None
    MTGThemeIntelligence = None

try:
    from .themes.halo4 import get_halo4_theme, Halo4ThemeIntelligence
except ImportError:
    get_halo4_theme = None
    Halo4ThemeIntelligence = None

try:
    from .themes.nazi import get_nazi_theme, NaziThemeIntelligence
except ImportError:
    get_nazi_theme = None
    NaziThemeIntelligence = None

try:
    from .themes.cyberpunk import get_cyberpunk_theme, CyberpunkThemeIntelligence
except ImportError:
    get_cyberpunk_theme = None
    CyberpunkThemeIntelligence = None


class ThemeConfig:
    """Theme configuration manager"""
    
    THEMES = {
        'matrix': {
            'name': 'Matrix',
            'description': 'Matrix movie theme with green code rain effects',
            'audio_enabled': True,
            'audio_file': 'matrix/ambient_1min.mp3',
            'audio_loop': True,
            'audio_volume': 0.3,  # 30% volume
            'effects': ['code_rain', 'glitch', 'digital_transitions'],
            'colors': {
                'primary': '#00ff00',
                'secondary': '#00ff88',
                'background': '#000000',
                'accent': '#00ffff'
            },
            'color_grading': 'matrix',
            'font_family': 'monospace',
            'transition_type': 'digital'
        },
        'cyberpunk': {
            'name': 'Cyberpunk',
            'description': 'Cyberpunk future theme with neon colors',
            'audio_enabled': True,
            'audio_file': 'cyberpunk/ambient.mp3',
            'audio_loop': True,
            'audio_volume': 0.25,
            'effects': ['neon_glow', 'scan_lines', 'hologram'],
            'colors': {
                'primary': '#ff00ff',
                'secondary': '#00ffff',
                'background': '#0a0a1a',
                'accent': '#ff0080'
            },
            'color_grading': 'cyberpunk',
            'font_family': 'sans-serif',
            'transition_type': 'smooth'
        },
        'sci-fi': {
            'name': 'Sci-Fi',
            'description': 'General science fiction theme',
            'audio_enabled': True,
            'audio_file': 'sci-fi/ambient.mp3',
            'audio_loop': True,
            'audio_volume': 0.2,
            'effects': ['particles', 'energy_waves'],
            'colors': {
                'primary': '#00aaff',
                'secondary': '#0088ff',
                'background': '#000a1a',
                'accent': '#00ffaa'
            },
            'color_grading': 'sci-fi',
            'font_family': 'sans-serif',
            'transition_type': 'fade'
        },
        'nature': {
            'name': 'Nature',
            'description': 'Nature documentary theme',
            'audio_enabled': True,
            'audio_file': 'nature/ambient.mp3',
            'audio_loop': True,
            'audio_volume': 0.15,
            'effects': ['natural_transitions', 'fade'],
            'colors': {
                'primary': '#4a7c59',
                'secondary': '#8fbc8f',
                'background': '#1a2a1a',
                'accent': '#90ee90'
            },
            'color_grading': 'nature',
            'font_family': 'serif',
            'transition_type': 'fade'
        },
        'default': {
            'name': 'Default',
            'description': 'Default theme',
            'audio_enabled': False,
            'effects': [],
            'colors': {
                'primary': '#ffffff',
                'secondary': '#cccccc',
                'background': '#000000',
                'accent': '#888888'
            },
            'color_grading': 'default',
            'font_family': 'sans-serif',
            'transition_type': 'fade'
        },
        'mtg': {
            'name': 'Magic the Gathering',
            'description': 'MTG theme with intelligent mana color detection',
            'audio_enabled': True,
            'audio_file': 'mtg/ambient.mp3',
            'audio_loop': True,
            'audio_volume': 0.25,
            'effects': ['mana_swirls', 'card_flip', 'spell_effects'],
            'colors': {
                'primary': '#f9faf4',
                'secondary': '#0e68ab',
                'background': '#1a0f0a',
                'accent': '#d3202a'
            },
            'color_grading': 'mtg',
            'font_family': 'serif',
            'transition_type': 'card_flip',
            'intelligent': True
        },
        'halo4': {
            'name': 'Halo 4',
            'description': 'Halo 4 theme with faction detection',
            'audio_enabled': True,
            'audio_file': 'halo4/ambient.mp3',
            'audio_loop': True,
            'audio_volume': 0.3,
            'effects': ['plasma_effects', 'shield_energy', 'hud_overlay'],
            'colors': {
                'primary': '#4a90e2',
                'secondary': '#00ffff',
                'background': '#0a0a1a',
                'accent': '#ff4500'
            },
            'color_grading': 'halo',
            'font_family': 'sans-serif',
            'transition_type': 'digital',
            'intelligent': True
        },
        'nazi_wwii': {
            'name': 'WWII Historical',
            'description': 'WWII historical theme with era detection',
            'audio_enabled': True,
            'audio_file': 'wwii/ambient.mp3',
            'audio_loop': True,
            'audio_volume': 0.2,
            'effects': ['film_grain', 'vintage', 'document_flip'],
            'colors': {
                'primary': '#8b0000',
                'secondary': '#000000',
                'background': '#1a1a1a',
                'accent': '#ffd700'
            },
            'color_grading': 'sepia',
            'font_family': 'serif',
            'transition_type': 'fade',
            'intelligent': True,
            'sensitivity_warning': True
        }
    }
    
    @classmethod
    def get_theme(cls, theme_name: str, prompt: str = None, title: str = None) -> Dict[str, Any]:
        """Get theme configuration with intelligence
        
        Args:
            theme_name: Name of theme
            prompt: Optional prompt for intelligent theme detection
            title: Optional title for intelligent theme detection
        
        Returns:
            Theme configuration dict with intelligence applied
        """
        theme_name_lower = theme_name.lower()
        base_theme = cls.THEMES.get(theme_name_lower, cls.THEMES['default'])
        
        # Apply intelligence if theme supports it
        if base_theme.get('intelligent', False):
            if theme_name_lower == 'mtg' and get_mtg_theme:
                intelligent_theme = get_mtg_theme(prompt, title)
                # Merge intelligent theme with base
                base_theme = {**base_theme, **intelligent_theme}
            elif theme_name_lower == 'halo4' and get_halo4_theme:
                intelligent_theme = get_halo4_theme(prompt, title)
                base_theme = {**base_theme, **intelligent_theme}
            elif theme_name_lower == 'nazi_wwii' and get_nazi_theme:
                intelligent_theme = get_nazi_theme(prompt, title)
                base_theme = {**base_theme, **intelligent_theme}
        
        return base_theme
    
    @classmethod
    def get_audio_path(cls, theme_name: str) -> Optional[str]:
        """Get audio file path for theme
        
        Args:
            theme_name: Name of theme
        
        Returns:
            Path to audio file or None
        """
        theme = cls.get_theme(theme_name)
        if not theme.get('audio_enabled', False):
            return None
        
        audio_file = theme.get('audio_file')
        if not audio_file:
            return None
        
        # Check if audio file exists in static folder
        static_audio_path = Path(__file__).parent.parent.parent / 'web' / 'static' / 'audio' / audio_file
        if static_audio_path.exists():
            return str(static_audio_path)
        
        # Try relative path
        relative_path = f"/static/audio/{audio_file}"
        return relative_path
    
    @classmethod
    def list_themes(cls) -> list:
        """List all available themes"""
        return list(cls.THEMES.keys())
    
    @classmethod
    def is_audio_enabled(cls, theme_name: str) -> bool:
        """Check if audio is enabled for theme"""
        theme = cls.get_theme(theme_name)
        return theme.get('audio_enabled', False)
    
    @classmethod
    def get_color_grading(cls, theme_name: str) -> str:
        """Get color grading type for theme"""
        theme = cls.get_theme(theme_name)
        return theme.get('color_grading', 'default')


def get_theme_config(theme_name: str) -> Dict[str, Any]:
    """Get theme configuration (convenience function)"""
    return ThemeConfig.get_theme(theme_name)

