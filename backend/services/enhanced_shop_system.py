"""
Enhanced Shop System with Theme Boosters, Random Creation, and Trophy Integration
"""
import uuid
import random
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class ThemeBooster:
    """Theme booster with random creation capabilities"""
    
    def __init__(self, booster_id: str, name: str, price: int, rarity: str = 'rare'):
        self.id = booster_id
        self.name = name
        self.price = price
        self.rarity = rarity
        self.created_at = datetime.utcnow()
        self.uses = 0
        self.max_uses = random.randint(3, 10)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price': self.price,
            'rarity': self.rarity,
            'uses': self.uses,
            'max_uses': self.max_uses,
            'created_at': self.created_at.isoformat()
        }


class EnhancedShopSystem:
    """Enhanced shop with theme boosters, random creation, and trophy integration"""
    
    def __init__(self):
        self.theme_boosters = {}  # {booster_id: ThemeBooster}
        self.random_creations = {}  # {creation_id: creation_data}
        self.trophy_items = {}  # {item_id: trophy_item_data}
        self.user_boosters = defaultdict(list)  # {user_id: [booster_ids]}
        self.user_creations = defaultdict(list)  # {user_id: [creation_ids]}
        self._initialize_theme_boosters()
        self._initialize_trophy_items()
    
    def _initialize_theme_boosters(self):
        """Initialize theme boosters"""
        boosters = [
            ThemeBooster('booster_theme_random', 'Random Theme Booster', 800, 'rare'),
            ThemeBooster('booster_theme_epic', 'Epic Theme Booster', 1500, 'epic'),
            ThemeBooster('booster_theme_legendary', 'Legendary Theme Booster', 3000, 'legendary'),
            ThemeBooster('booster_theme_madness', 'Madness Theme Booster', 5000, 'mythic'),
            ThemeBooster('booster_theme_all', 'All Themes Unlock Booster', 4000, 'legendary'),
        ]
        for booster in boosters:
            self.theme_boosters[booster.id] = booster
    
    def _initialize_trophy_items(self):
        """Initialize trophy items for shop"""
        trophies = [
            {
                'id': 'trophy_battle_victor',
                'name': 'Battle Victor Trophy',
                'description': 'Awarded for winning battles',
                'price': 2000,
                'rarity': 'epic',
                'icon': '🏆',
                'effects': {'battle_win_bonus': 0.15}
            },
            {
                'id': 'trophy_video_master',
                'name': 'Video Master Trophy',
                'description': 'Awarded for creating 100 videos',
                'price': 3000,
                'rarity': 'legendary',
                'icon': '🎬',
                'effects': {'video_quality_bonus': 0.2}
            },
            {
                'id': 'trophy_social_legend',
                'name': 'Social Legend Trophy',
                'description': 'Awarded for social achievements',
                'price': 2500,
                'rarity': 'epic',
                'icon': '👥',
                'effects': {'social_bonus': 0.1}
            },
            {
                'id': 'trophy_warzone_champion',
                'name': 'WarZone Champion Trophy',
                'description': 'Awarded for WarZone victories',
                'price': 5000,
                'rarity': 'mythic',
                'icon': '⚔️',
                'effects': {'warzone_power': 0.25}
            },
            {
                'id': 'trophy_collector',
                'name': 'Master Collector Trophy',
                'description': 'Awarded for collecting items',
                'price': 1500,
                'rarity': 'rare',
                'icon': '💎',
                'effects': {'collection_bonus': 0.1}
            },
        ]
        for trophy in trophies:
            self.trophy_items[trophy['id']] = trophy
    
    def create_random_theme_booster(self, user_id: str, booster_type: str = 'random') -> Dict[str, Any]:
        """Create a random theme booster"""
        booster_id = str(uuid.uuid4())
        
        # Random theme selection
        themes = ['wwii', 'mtg', 'ctrl_a_delete', 'the_end', 'slaprygler', 'voldsrov', 'cyberpunk', 'sci_fi', 'nature']
        selected_themes = random.sample(themes, random.randint(1, 3))
        
        booster = {
            'id': booster_id,
            'type': booster_type,
            'themes': selected_themes,
            'power': random.randint(50, 200),
            'duration': random.randint(3600, 7200),  # 1-2 hours
            'created_at': datetime.utcnow().isoformat(),
            'user_id': user_id
        }
        
        self.random_creations[booster_id] = booster
        self.user_creations[user_id].append(booster_id)
        
        return {
            'success': True,
            'booster': booster,
            'message': f'Created random theme booster with {len(selected_themes)} themes'
        }
    
    def purchase_theme_booster(self, user_id: str, booster_id: str) -> Dict[str, Any]:
        """Purchase a theme booster"""
        booster = self.theme_boosters.get(booster_id)
        if not booster:
            return {'success': False, 'error': 'Booster not found'}
        
        if booster.uses >= booster.max_uses:
            return {'success': False, 'error': 'Booster exhausted'}
        
        booster.uses += 1
        self.user_boosters[user_id].append(booster_id)
        
        # Generate random theme unlock
        themes = ['wwii', 'mtg', 'ctrl_a_delete', 'the_end', 'slaprygler', 'voldsrov']
        unlocked_theme = random.choice(themes)
        
        return {
            'success': True,
            'booster': booster.to_dict(),
            'unlocked_theme': unlocked_theme,
            'message': f'Theme booster activated! Unlocked: {unlocked_theme}'
        }
    
    def purchase_trophy(self, user_id: str, trophy_id: str) -> Dict[str, Any]:
        """Purchase a trophy from shop"""
        trophy = self.trophy_items.get(trophy_id)
        if not trophy:
            return {'success': False, 'error': 'Trophy not found'}
        
        return {
            'success': True,
            'trophy': trophy,
            'message': f'Purchased {trophy["name"]}'
        }
    
    def get_available_boosters(self) -> List[Dict]:
        """Get all available theme boosters"""
        return [booster.to_dict() for booster in self.theme_boosters.values()]
    
    def get_available_trophies(self) -> List[Dict]:
        """Get all available trophy items"""
        return list(self.trophy_items.values())
    
    def get_user_creations(self, user_id: str) -> List[Dict]:
        """Get user's random creations"""
        creation_ids = self.user_creations.get(user_id, [])
        return [self.random_creations.get(cid) for cid in creation_ids if cid in self.random_creations]


# Global instance
enhanced_shop_system = EnhancedShopSystem()

