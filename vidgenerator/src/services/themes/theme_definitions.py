"""
Complete Theme Definitions - All 12 Themes Hardcoded
Includes all properties, bonuses, defense mechanisms, and logic
"""
from typing import Dict, List, Optional
from enum import Enum

class ThemeType(Enum):
    """All 12 theme types"""
    MATRIX = "matrix"
    CYBERPUNK = "cyberpunk"
    SCI_FI = "sci-fi"
    NATURE = "nature"
    MTG = "mtg"
    HALO4 = "halo4"
    WWII = "wwii"
    FANTASY = "fantasy"
    HORROR = "horror"
    COMEDY = "comedy"
    ROMANCE = "romance"
    ACTION = "action"

class ThemeDefinitions:
    """Complete hardcoded theme definitions"""
    
    def __init__(self):
        self.themes = {
            ThemeType.MATRIX.value: {
                'name': 'Matrix',
                'display_name': 'The Matrix',
                'xp_multiplier': 1.5,
                'difficulty': 'medium',
                'color': '#00ff00',
                'defense_bonus': 1.2,
                'description': 'Enter the digital realm where reality is code',
                'icon': '🎬',
                'background_style': 'matrix-rain',
                'recommended_skills': ['logic', 'technical', 'strategic'],
                'enemy_resistance': 0.8,
                'hack_bonus': 1.3,
                'special_abilities': ['code_manipulation', 'reality_bend', 'bullet_time'],
                'story_elements': ['red_pill', 'blue_pill', 'agent_smith', 'morpheus', 'neo'],
                'music_style': 'electronic',
                'atmosphere': 'dark_tech',
                'generation_prompts': [
                    'Matrix-style digital rain',
                    'Green code falling',
                    'Virtual reality glitch',
                    'Neo fighting agents',
                    'Red pill blue pill choice'
                ]
            },
            ThemeType.CYBERPUNK.value: {
                'name': 'Cyberpunk',
                'display_name': 'Cyberpunk 2077',
                'xp_multiplier': 1.3,
                'difficulty': 'medium',
                'color': '#ff00ff',
                'defense_bonus': 1.1,
                'description': 'Neon-lit streets of the future',
                'icon': '🌃',
                'background_style': 'neon-city',
                'recommended_skills': ['social', 'technical', 'psychological'],
                'enemy_resistance': 0.85,
                'hack_bonus': 1.4,
                'special_abilities': ['cyberware', 'netrunning', 'street_smart'],
                'story_elements': ['night_city', 'corpos', 'netrunners', 'cyberware', 'braindance'],
                'music_style': 'synthwave',
                'atmosphere': 'neon_noir',
                'generation_prompts': [
                    'Neon-lit cyberpunk city',
                    'Futuristic street market',
                    'Cyberware implants',
                    'Holographic advertisements',
                    'Night city skyline'
                ]
            },
            ThemeType.SCI_FI.value: {
                'name': 'Sci-Fi',
                'display_name': 'Science Fiction',
                'xp_multiplier': 1.2,
                'difficulty': 'easy',
                'color': '#00ccff',
                'defense_bonus': 1.0,
                'description': 'Explore the cosmos and future technology',
                'icon': '🚀',
                'background_style': 'space',
                'recommended_skills': ['logic', 'technical', 'organization'],
                'enemy_resistance': 0.9,
                'hack_bonus': 1.1,
                'special_abilities': ['space_travel', 'alien_contact', 'future_tech'],
                'story_elements': ['spaceships', 'aliens', 'planets', 'space_stations', 'time_travel'],
                'music_style': 'ambient_space',
                'atmosphere': 'cosmic_wonder',
                'generation_prompts': [
                    'Alien planet landscape',
                    'Spaceship interior',
                    'Futuristic space station',
                    'Alien encounter',
                    'Cosmic nebula'
                ]
            },
            ThemeType.NATURE.value: {
                'name': 'Nature',
                'display_name': 'Nature & Wildlife',
                'xp_multiplier': 1.0,
                'difficulty': 'easy',
                'color': '#00ff88',
                'defense_bonus': 0.9,
                'description': 'Immerse yourself in the natural world',
                'icon': '🌿',
                'background_style': 'forest',
                'recommended_skills': ['social', 'organization', 'psychological'],
                'enemy_resistance': 0.95,
                'hack_bonus': 0.8,
                'special_abilities': ['animal_communication', 'plant_growth', 'weather_control'],
                'story_elements': ['forests', 'animals', 'mountains', 'oceans', 'seasons'],
                'music_style': 'nature_sounds',
                'atmosphere': 'peaceful_natural',
                'generation_prompts': [
                    'Majestic mountain range',
                    'Dense forest path',
                    'Ocean waves crashing',
                    'Wildlife in habitat',
                    'Sunset over nature'
                ]
            },
            ThemeType.MTG.value: {
                'name': 'MTG',
                'display_name': 'Magic: The Gathering',
                'xp_multiplier': 1.4,
                'difficulty': 'hard',
                'color': '#ffaa00',
                'defense_bonus': 1.3,
                'description': 'Battle with spells and creatures',
                'icon': '🃏',
                'background_style': 'magical',
                'recommended_skills': ['strategic', 'logic', 'psychological'],
                'enemy_resistance': 0.75,
                'hack_bonus': 1.2,
                'special_abilities': ['spell_casting', 'creature_summon', 'mana_manipulation'],
                'story_elements': ['planeswalkers', 'spells', 'creatures', 'artifacts', 'lands'],
                'music_style': 'epic_fantasy',
                'atmosphere': 'magical_battle',
                'generation_prompts': [
                    'Magic spell being cast',
                    'Fantasy creature battle',
                    'Mana crystals glowing',
                    'Planeswalker duel',
                    'Magical artifact'
                ]
            },
            ThemeType.HALO4.value: {
                'name': 'Halo 4',
                'display_name': 'Halo 4',
                'xp_multiplier': 1.6,
                'difficulty': 'hard',
                'color': '#00aaff',
                'defense_bonus': 1.4,
                'description': 'Master Chief returns in epic sci-fi warfare',
                'icon': '🎮',
                'background_style': 'halo',
                'recommended_skills': ['technical', 'strategic', 'organization'],
                'enemy_resistance': 0.7,
                'hack_bonus': 1.5,
                'special_abilities': ['spartan_armor', 'covenant_tech', 'forerunner_artifacts'],
                'story_elements': ['master_chief', 'cortana', 'covenant', 'forerunners', 'halo_rings'],
                'music_style': 'epic_orchestral',
                'atmosphere': 'epic_warfare',
                'generation_prompts': [
                    'Master Chief in action',
                    'Halo ring in space',
                    'Covenant ship battle',
                    'Forerunner structure',
                    'Spartan armor detail'
                ]
            },
            ThemeType.WWII.value: {
                'name': 'WWII',
                'display_name': 'World War II',
                'xp_multiplier': 1.1,
                'difficulty': 'medium',
                'color': '#ccaa00',
                'defense_bonus': 1.1,
                'description': 'Historical warfare and resistance',
                'icon': '⚔️',
                'background_style': 'war',
                'recommended_skills': ['organization', 'strategic', 'social'],
                'enemy_resistance': 0.85,
                'hack_bonus': 1.0,
                'special_abilities': ['tactical_planning', 'resistance_network', 'intelligence'],
                'story_elements': ['battlefields', 'resistance', 'allies', 'axis', 'd_day'],
                'music_style': 'military_march',
                'atmosphere': 'historical_war',
                'generation_prompts': [
                    'WWII battlefield',
                    'Resistance fighters',
                    'Allied forces',
                    'Historical war scene',
                    'Military strategy'
                ]
            },
            ThemeType.FANTASY.value: {
                'name': 'Fantasy',
                'display_name': 'Fantasy',
                'xp_multiplier': 1.3,
                'difficulty': 'medium',
                'color': '#aa00ff',
                'defense_bonus': 1.2,
                'description': 'Dragons, magic, and epic quests',
                'icon': '🐉',
                'background_style': 'fantasy',
                'recommended_skills': ['psychological', 'strategic', 'social'],
                'enemy_resistance': 0.8,
                'hack_bonus': 1.1,
                'special_abilities': ['magic_spells', 'dragon_riding', 'quest_completion'],
                'story_elements': ['dragons', 'wizards', 'castles', 'quests', 'magic_items'],
                'music_style': 'epic_fantasy',
                'atmosphere': 'magical_adventure',
                'generation_prompts': [
                    'Dragon flying over castle',
                    'Wizard casting spell',
                    'Fantasy landscape',
                    'Magic sword glowing',
                    'Epic quest scene'
                ]
            },
            ThemeType.HORROR.value: {
                'name': 'Horror',
                'display_name': 'Horror',
                'xp_multiplier': 1.7,
                'difficulty': 'hard',
                'color': '#ff0000',
                'defense_bonus': 1.5,
                'description': 'Face your fears in the darkness',
                'icon': '👻',
                'background_style': 'horror',
                'recommended_skills': ['psychological', 'logic', 'strategic'],
                'enemy_resistance': 0.6,
                'hack_bonus': 1.6,
                'special_abilities': ['fear_resistance', 'survival_instinct', 'investigation'],
                'story_elements': ['ghosts', 'monsters', 'haunted_places', 'survival', 'mystery'],
                'music_style': 'dark_ambient',
                'atmosphere': 'terrifying_dark',
                'generation_prompts': [
                    'Haunted house interior',
                    'Dark forest path',
                    'Horror creature',
                    'Spooky atmosphere',
                    'Survival horror scene'
                ]
            },
            ThemeType.COMEDY.value: {
                'name': 'Comedy',
                'display_name': 'Comedy',
                'xp_multiplier': 0.9,
                'difficulty': 'easy',
                'color': '#ffff00',
                'defense_bonus': 0.8,
                'description': 'Laugh your way through adventures',
                'icon': '😂',
                'background_style': 'bright',
                'recommended_skills': ['social', 'psychological', 'organization'],
                'enemy_resistance': 1.1,
                'hack_bonus': 0.9,
                'special_abilities': ['humor', 'comic_timing', 'audience_connection'],
                'story_elements': ['jokes', 'funny_situations', 'comedy_acts', 'laughter', 'entertainment'],
                'music_style': 'upbeat_comedy',
                'atmosphere': 'light_hearted',
                'generation_prompts': [
                    'Funny situation',
                    'Comedy performance',
                    'Laughing characters',
                    'Comic scene',
                    'Entertainment show'
                ]
            },
            ThemeType.ROMANCE.value: {
                'name': 'Romance',
                'display_name': 'Romance',
                'xp_multiplier': 1.0,
                'difficulty': 'easy',
                'color': '#ff88cc',
                'defense_bonus': 0.9,
                'description': 'Love stories and emotional connections',
                'icon': '💕',
                'background_style': 'romantic',
                'recommended_skills': ['social', 'psychological', 'organization'],
                'enemy_resistance': 1.0,
                'hack_bonus': 0.85,
                'special_abilities': ['emotional_connection', 'romance', 'relationship_building'],
                'story_elements': ['love_stories', 'romantic_scenes', 'relationships', 'emotions', 'heartfelt'],
                'music_style': 'romantic',
                'atmosphere': 'warm_emotional',
                'generation_prompts': [
                    'Romantic sunset',
                    'Couple together',
                    'Love story scene',
                    'Emotional moment',
                    'Romantic setting'
                ]
            },
            ThemeType.ACTION.value: {
                'name': 'Action',
                'display_name': 'Action',
                'xp_multiplier': 1.5,
                'difficulty': 'hard',
                'color': '#ff3300',
                'defense_bonus': 1.3,
                'description': 'High-octane action and adrenaline',
                'icon': '💥',
                'background_style': 'action',
                'recommended_skills': ['strategic', 'technical', 'organization'],
                'enemy_resistance': 0.75,
                'hack_bonus': 1.4,
                'special_abilities': ['adrenaline_rush', 'combat_mastery', 'tactical_combat'],
                'story_elements': ['explosions', 'car_chases', 'fight_scenes', 'stunts', 'adrenaline'],
                'music_style': 'intense_action',
                'atmosphere': 'high_energy',
                'generation_prompts': [
                    'Explosive action scene',
                    'Car chase sequence',
                    'Fight scene',
                    'Stunt performance',
                    'High-speed action'
                ]
            }
        }
    
    def get_theme(self, theme_key: str) -> Optional[Dict]:
        """Get theme by key"""
        return self.themes.get(theme_key)
    
    def get_all_themes(self) -> Dict:
        """Get all themes"""
        return self.themes
    
    def get_theme_list(self) -> List[Dict]:
        """Get themes as list with keys"""
        return [
            {**theme_data, 'key': key}
            for key, theme_data in self.themes.items()
        ]
    
    def get_theme_by_type(self, theme_type: ThemeType) -> Optional[Dict]:
        """Get theme by ThemeType enum"""
        return self.themes.get(theme_type.value)
    
    def get_recommended_defense_mechanism(self, theme_key: str) -> str:
        """Get recommended defense mechanism for theme"""
        theme = self.get_theme(theme_key)
        if not theme:
            return 'sublimation'
        
        # Map themes to defense mechanisms
        mechanism_map = {
            'matrix': 'intellectualization',
            'cyberpunk': 'projection',
            'sci-fi': 'rationalization',
            'nature': 'sublimation',
            'mtg': 'identification',
            'halo4': 'reaction_formation',
            'wwii': 'compensation',
            'fantasy': 'identification',
            'horror': 'repression',
            'comedy': 'sublimation',
            'romance': 'sublimation',
            'action': 'reaction_formation'
        }
        
        return mechanism_map.get(theme_key, 'sublimation')
    
    def get_theme_enemy_match(self, theme_key: str) -> str:
        """Get matching enemy type for theme"""
        theme = self.get_theme(theme_key)
        if not theme:
            return 'competitor'
        
        # Map themes to enemy types
        enemy_map = {
            'matrix': 'hacker',
            'cyberpunk': 'hacker',
            'sci-fi': 'corporate',
            'nature': 'competitor',
            'mtg': 'rival_platform',
            'halo4': 'government',
            'wwii': 'government',
            'fantasy': 'rival_platform',
            'horror': 'hacker',
            'comedy': 'competitor',
            'romance': 'competitor',
            'action': 'corporate'
        }
        
        return enemy_map.get(theme_key, 'competitor')

# Initialize theme definitions
theme_definitions = ThemeDefinitions()

