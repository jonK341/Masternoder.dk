"""
Theme Intelligence Modules
Intelligent theme systems for Magic the Gathering, Halo 4, and WWII/Nazi
"""

from .magic_gathering import get_mtg_theme, MTGThemeIntelligence
from .halo4 import get_halo4_theme, Halo4ThemeIntelligence
from .nazi import get_nazi_theme, NaziThemeIntelligence
from .cyberpunk import get_cyberpunk_theme, CyberpunkThemeIntelligence

__all__ = [
    'get_mtg_theme',
    'MTGThemeIntelligence',
    'get_halo4_theme',
    'Halo4ThemeIntelligence',
    'get_nazi_theme',
    'NaziThemeIntelligence',
    'get_cyberpunk_theme',
    'CyberpunkThemeIntelligence'
]

