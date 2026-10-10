"""
Visual Game Engine - Graphics and Visual Experience
"""
import uuid
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict


class VisualEffect:
    """Represents a visual effect"""
    
    def __init__(self, effect_id: str, name: str, effect_type: str, properties: Dict):
        self.id = effect_id
        self.name = name
        self.type = effect_type  # particle, animation, shader, overlay
        self.properties = properties
        self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'properties': self.properties,
            'created_at': self.created_at.isoformat()
        }


class GraphicsAsset:
    """Represents a graphics asset"""
    
    def __init__(self, asset_id: str, name: str, asset_type: str, url: str, metadata: Dict = None):
        self.id = asset_id
        self.name = name
        self.type = asset_type  # sprite, texture, model, animation
        self.url = url
        self.metadata = metadata or {}
        self.created_at = datetime.utcnow()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'url': self.url,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat()
        }


class VisualGameEngine:
    """Manages visual game experience with graphics"""
    
    def __init__(self):
        self.visual_effects = {}  # {effect_id: VisualEffect}
        self.graphics_assets = {}  # {asset_id: GraphicsAsset}
        self.active_effects = defaultdict(list)  # {user_id: [effect_ids]}
        self.scenes = {}  # {scene_id: scene_data}
        self._initialize_default_assets()
    
    def _initialize_default_assets(self):
        """Initialize default graphics assets"""
        default_assets = [
            GraphicsAsset('bg_battle', 'Battle Background', 'texture', '/static/img/battle-bg.jpg', {'width': 1920, 'height': 1080}),
            GraphicsAsset('particle_fire', 'Fire Particle', 'particle', '/static/img/particles/fire.png', {'duration': 2.0}),
            GraphicsAsset('particle_ice', 'Ice Particle', 'particle', '/static/img/particles/ice.png', {'duration': 1.5}),
            GraphicsAsset('particle_lightning', 'Lightning Particle', 'particle', '/static/img/particles/lightning.png', {'duration': 0.5}),
            GraphicsAsset('sprite_character', 'Character Sprite', 'sprite', '/static/img/sprites/character.png', {'frames': 8}),
        ]
        
        for asset in default_assets:
            self.graphics_assets[asset.id] = asset
    
    def create_visual_effect(self, name: str, effect_type: str, properties: Dict = None) -> Dict[str, Any]:
        """Create a visual effect"""
        effect_id = str(uuid.uuid4())
        effect = VisualEffect(effect_id, name, effect_type, properties)
        self.visual_effects[effect_id] = effect
        
        return {
            'success': True,
            'effect_id': effect_id,
            'effect': effect.to_dict()
        }
    
    def add_graphics_asset(self, name: str, asset_type: str, url: str, metadata: Dict = None) -> Dict[str, Any]:
        """Add a graphics asset"""
        asset_id = str(uuid.uuid4())
        asset = GraphicsAsset(asset_id, name, asset_type, url, metadata)
        self.graphics_assets[asset_id] = asset
        
        return {
            'success': True,
            'asset_id': asset_id,
            'asset': asset.to_dict()
        }
    
    def add_graphics_asset(self, name: str, asset_type: str, url: str, metadata: Dict = None) -> Dict[str, Any]:
        """Add a graphics asset"""
        asset_id = str(uuid.uuid4())
        asset = GraphicsAsset(asset_id, name, asset_type, url, metadata)
        self.graphics_assets[asset_id] = asset
        
        return {
            'success': True,
            'asset_id': asset_id,
            'asset': asset.to_dict()
        }
    
    def activate_effect(self, user_id: str, effect_id: str) -> Dict[str, Any]:
        """Activate a visual effect for a user"""
        if effect_id not in self.visual_effects:
            return {'success': False, 'error': 'Effect not found'}
        
        if effect_id not in self.active_effects[user_id]:
            self.active_effects[user_id].append(effect_id)
        
        return {
            'success': True,
            'effect': self.visual_effects[effect_id].to_dict(),
            'message': 'Effect activated'
        }
    
    def create_scene(self, name: str, scene_type: str, assets: List[str], effects: List[str] = None) -> Dict[str, Any]:
        """Create a visual scene"""
        scene_id = str(uuid.uuid4())
        scene = {
            'id': scene_id,
            'name': name,
            'type': scene_type,
            'assets': assets,
            'effects': effects or [],
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.scenes[scene_id] = scene
        
        return {
            'success': True,
            'scene_id': scene_id,
            'scene': scene
        }
    
    def get_user_visual_state(self, user_id: str) -> Dict[str, Any]:
        """Get user's current visual state"""
        active_effect_ids = self.active_effects.get(user_id, [])
        active_effects = [self.visual_effects[eid].to_dict() for eid in active_effect_ids if eid in self.visual_effects]
        
        return {
            'user_id': user_id,
            'active_effects': active_effects,
            'graphics_assets': [asset.to_dict() for asset in self.graphics_assets.values()]
        }
    
    def get_all_assets(self) -> List[Dict]:
        """Get all graphics assets"""
        return [asset.to_dict() for asset in self.graphics_assets.values()]


# Global instance
visual_game_engine = VisualGameEngine()

