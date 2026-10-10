"""
Visual Game Experience System - Graphics and Visual Effects
"""
import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict
from enum import Enum


class GraphicsType(Enum):
    """Types of graphics"""
    PARTICLE = "particle"
    SPRITE = "sprite"
    ANIMATION = "animation"
    EFFECT = "effect"
    UI = "ui"
    BACKGROUND = "background"


class VisualEffect:
    """Represents a visual effect"""
    
    def __init__(self, effect_id: str, name: str, effect_type: str, graphics_type: GraphicsType):
        self.id = effect_id
        self.name = name
        self.type = effect_type
        self.graphics_type = graphics_type
        self.created_at = datetime.utcnow()
        self.properties = {}
        self.duration = 0
        self.intensity = 1.0
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'graphics_type': self.graphics_type.value,
            'properties': self.properties,
            'duration': self.duration,
            'intensity': self.intensity,
            'created_at': self.created_at.isoformat()
        }


class VisualGameExperience:
    """Manages visual game experience with graphics"""
    
    def __init__(self):
        self.effects = {}  # {effect_id: VisualEffect}
        self.active_effects = {}  # {user_id: [effect_ids]}
        self.graphics_library = {}  # {graphic_id: graphic_data}
        self.visual_settings = {}  # {user_id: settings}
        self._initialize_graphics_library()
    
    def _initialize_graphics_library(self):
        """Initialize graphics library"""
        graphics = [
            {
                'id': 'particle_fire',
                'name': 'Fire Particles',
                'type': GraphicsType.PARTICLE,
                'url': '/static/graphics/particles/fire.json',
                'preview': '/static/graphics/particles/fire_preview.png'
            },
            {
                'id': 'particle_ice',
                'name': 'Ice Particles',
                'type': GraphicsType.PARTICLE,
                'url': '/static/graphics/particles/ice.json',
                'preview': '/static/graphics/particles/ice_preview.png'
            },
            {
                'id': 'sprite_character',
                'name': 'Character Sprite',
                'type': GraphicsType.SPRITE,
                'url': '/static/graphics/sprites/character.png',
                'preview': '/static/graphics/sprites/character_preview.png'
            },
            {
                'id': 'animation_battle',
                'name': 'Battle Animation',
                'type': GraphicsType.ANIMATION,
                'url': '/static/graphics/animations/battle.json',
                'preview': '/static/graphics/animations/battle_preview.gif'
            },
            {
                'id': 'effect_lightning',
                'name': 'Lightning Effect',
                'type': GraphicsType.EFFECT,
                'url': '/static/graphics/effects/lightning.json',
                'preview': '/static/graphics/effects/lightning_preview.png'
            },
            {
                'id': 'ui_panel',
                'name': 'UI Panel',
                'type': GraphicsType.UI,
                'url': '/static/graphics/ui/panel.png',
                'preview': '/static/graphics/ui/panel_preview.png'
            },
            {
                'id': 'background_fantasy',
                'name': 'Fantasy Background',
                'type': GraphicsType.BACKGROUND,
                'url': '/static/graphics/backgrounds/fantasy.jpg',
                'preview': '/static/graphics/backgrounds/fantasy_preview.jpg'
            }
        ]
        
        for graphic in graphics:
            self.graphics_library[graphic['id']] = graphic
    
    def create_effect(self, name: str, effect_type: str, graphics_type: GraphicsType, 
                     properties: Dict = None, duration: int = 0) -> Dict[str, Any]:
        """Create a visual effect"""
        effect_id = str(uuid.uuid4())
        effect = VisualEffect(effect_id, name, effect_type, graphics_type)
        effect.properties = properties or {}
        effect.duration = duration
        
        self.effects[effect_id] = effect
        
        return {
            'success': True,
            'effect_id': effect_id,
            'effect': effect.to_dict()
        }
    
    def activate_effect(self, user_id: str, effect_id: str) -> Dict[str, Any]:
        """Activate an effect for a user"""
        effect = self.effects.get(effect_id)
        if not effect:
            return {'success': False, 'error': 'Effect not found'}
        
        if user_id not in self.active_effects:
            self.active_effects[user_id] = []
        
        if effect_id not in self.active_effects[user_id]:
            self.active_effects[user_id].append(effect_id)
        
        return {
            'success': True,
            'effect': effect.to_dict(),
            'message': f'Effect {effect.name} activated'
        }
    
    def get_graphics_library(self, graphics_type: Optional[GraphicsType] = None) -> List[Dict]:
        """Get graphics library"""
        if graphics_type:
            return [g for g in self.graphics_library.values() if g['type'] == graphics_type]
        return list(self.graphics_library.values())
    
    def get_user_effects(self, user_id: str) -> List[Dict]:
        """Get user's active effects"""
        effect_ids = self.active_effects.get(user_id, [])
        return [self.effects[eid].to_dict() for eid in effect_ids if eid in self.effects]
    
    def set_visual_settings(self, user_id: str, settings: Dict) -> Dict[str, Any]:
        """Set visual settings for user"""
        self.visual_settings[user_id] = {
            **self.visual_settings.get(user_id, {}),
            **settings,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        return {
            'success': True,
            'settings': self.visual_settings[user_id]
        }
    
    def get_visual_settings(self, user_id: str) -> Dict:
        """Get visual settings for user"""
        default_settings = {
            'quality': 'high',
            'particles_enabled': True,
            'animations_enabled': True,
            'effects_enabled': True,
            'ui_theme': 'default'
        }
        
        return self.visual_settings.get(user_id, default_settings)


# Global instance
visual_game_experience = VisualGameExperience()

