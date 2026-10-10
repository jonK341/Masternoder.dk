"""
Game Shop & Marketplace
In-game currency, items, themes, power-ups, and cosmetic items
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class ShopItem:
    """Represents a shop item"""
    
    def __init__(self, item_id: str, name: str, description: str, price: int,
                 item_type: str, category: str = 'general', icon: str = '🛍️',
                 rarity: str = 'common', effects: Dict = None):
        self.id = item_id
        self.name = name
        self.description = description
        self.price = price
        self.type = item_type  # theme, power_up, cosmetic, unlock, currency
        self.category = category
        self.icon = icon
        self.rarity = rarity  # common, rare, epic, legendary
        self.effects = effects or {}
        self.available = True
        self.stock = -1  # -1 = unlimited
        self.purchased_count = 0
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,
            'type': self.type,
            'category': self.category,
            'icon': self.icon,
            'rarity': self.rarity,
            'effects': self.effects,
            'available': self.available,
            'stock': self.stock,
            'purchased_count': self.purchased_count
        }


class GameShop:
    """Manages game shop and marketplace"""
    
    def __init__(self):
        """Initialize shop"""
        self.items = {}
        self.user_currency = defaultdict(int)  # {user_id: currency_amount}
        self.user_inventory = defaultdict(list)  # {user_id: [item_ids]}
        self.purchase_history = defaultdict(list)  # {user_id: [purchases]}
        self._initialize_shop_items()
    
    def _initialize_shop_items(self):
        """Initialize shop items"""
        # Theme Unlocks
        themes = [
            ShopItem('theme_cyberpunk', 'Cyberpunk Theme', 'Unlock cyberpunk theme', 500,
                    'theme', 'themes', '🎨', 'rare'),
            ShopItem('theme_sci_fi', 'Sci-Fi Theme', 'Unlock sci-fi theme', 500,
                    'theme', 'themes', '🚀', 'rare'),
            ShopItem('theme_nature', 'Nature Theme', 'Unlock nature theme', 300,
                    'theme', 'themes', '🌲', 'common'),
            ShopItem('theme_wwii', 'World War II Theme', 'Historical WW2 documentary style with authentic period aesthetics', 800,
                    'theme', 'themes', '⚔️', 'epic', {'theme_id': 'wwii'}),
            ShopItem('theme_mtg', 'Magic: The Gathering Theme', 'Fantasy card game aesthetic with magical elements and epic battles', 1000,
                    'theme', 'themes', '🃏', 'legendary', {'theme_id': 'mtg'}),
            ShopItem('theme_ctrl_a_delete', 'Ctrl+A Delete Theme', 'Tech/cyberpunk theme with digital deletion and reset aesthetics', 700,
                    'theme', 'themes', '⌨️', 'rare', {'theme_id': 'ctrl_a_delete'}),
            ShopItem('theme_the_end', 'The End Theme', 'Apocalyptic and end-of-world theme with dramatic visuals', 900,
                    'theme', 'themes', '💀', 'epic', {'theme_id': 'the_end'}),
            ShopItem('theme_slaprygler', 'SlåPrygl%er Theme', 'Intense discipline and punishment theme with dramatic action', 850,
                    'theme', 'themes', '⚡', 'epic', {'theme_id': 'slaprygler', 'warning': 'Mature content'}),
            ShopItem('theme_voldsrov', 'VoldsRøv Theme', 'Intense battle theme with aggressive combat elements - Jons VoldsRøv ID = Ny §', 950,
                    'theme', 'themes', '⚔️', 'legendary', {'theme_id': 'voldsrov', 'special_id': 'Jons_VoldsRøv_ID_Ny_§'}),
            ShopItem('theme_all', 'All Themes Pack', 'Unlock all themes including new ones', 4000,
                    'theme', 'themes', '🎨', 'legendary'),
        ]
        
        # Power-ups
        power_ups = [
            ShopItem('xp_boost_1h', 'XP Boost (1h)', 'Double XP for 1 hour', 200,
                    'power_up', 'boosts', '⚡', 'common', {'xp_multiplier': 2.0, 'duration': 3600}),
            ShopItem('xp_boost_24h', 'XP Boost (24h)', 'Double XP for 24 hours', 1500,
                    'power_up', 'boosts', '⚡⚡', 'rare', {'xp_multiplier': 2.0, 'duration': 86400}),
            ShopItem('quality_boost', 'Quality Boost', 'Increase quality score by 0.1', 300,
                    'power_up', 'boosts', '⭐', 'rare', {'quality_bonus': 0.1}),
            ShopItem('stat_point', 'Stat Point', 'Gain 1 stat point', 400,
                    'power_up', 'boosts', '📊', 'common', {'stat_points': 1}),
        ]
        
        # Random Booster Packs
        random_boosters = [
            ShopItem('booster_mystery_common', 'Mystery Booster (Common)', 
                    'Random common item - could be XP boost, coins, or stat points', 150,
                    'power_up', 'boosts', '🎁', 'common', {'type': 'random_booster', 'rarity': 'common'}),
            ShopItem('booster_mystery_rare', 'Mystery Booster (Rare)', 
                    'Random rare item - higher chance of valuable boosts', 400,
                    'power_up', 'boosts', '🎁✨', 'rare', {'type': 'random_booster', 'rarity': 'rare'}),
            ShopItem('booster_mystery_epic', 'Mystery Booster (Epic)', 
                    'Random epic item - guaranteed powerful boost', 1000,
                    'power_up', 'boosts', '🎁⭐', 'epic', {'type': 'random_booster', 'rarity': 'epic'}),
            ShopItem('booster_mystery_legendary', 'Mystery Booster (Legendary)', 
                    'Random legendary item - ultimate power boost', 2500,
                    'power_up', 'boosts', '🎁💎', 'legendary', {'type': 'random_booster', 'rarity': 'legendary'}),
            ShopItem('booster_time_bonus', 'Time Bonus Booster', 
                    'Gain bonus game time rewards - extra XP and coins for playtime', 600,
                    'power_up', 'boosts', '⏰', 'rare', {'type': 'time_bonus', 'duration': 7200, 'time_multiplier': 1.5}),
            ShopItem('booster_luck_charm', 'Luck Charm Booster', 
                    'Increases chance of rare drops and random rewards', 500,
                    'power_up', 'boosts', '🍀', 'rare', {'type': 'luck_boost', 'luck_multiplier': 2.0, 'duration': 3600}),
            ShopItem('booster_energy_surge', 'Energy Surge Booster', 
                    'Instant energy refill + 50% energy regeneration boost', 350,
                    'power_up', 'boosts', '⚡💫', 'common', {'type': 'energy_surge', 'energy': 100, 'regen_boost': 1.5}),
            ShopItem('booster_mind_magi', 'Elsk Sindets Magi', 
                    'Mental clarity boost - enhances focus and creativity for video generation', 800,
                    'power_up', 'boosts', '🧠✨', 'epic', {'type': 'mind_magi', 'creativity_boost': 0.25, 'focus_boost': 0.3, 'duration': 3600}),
            # New Random Boosters
            ShopItem('booster_video_quality', 'Video Quality Booster', 
                    'Random quality boost for next video (0.05-0.25)', 750,
                    'power_up', 'boosts', '🎬⭐', 'epic', {'type': 'video_quality', 'quality_boost': 'random(0.05, 0.25)'}),
            ShopItem('booster_theme_unlock', 'Theme Mystery Unlock', 
                    '30% chance to unlock a random locked theme', 1200,
                    'power_up', 'boosts', '🎨🎁', 'epic', {'type': 'theme_unlock', 'unlock_chance': 0.3}),
            ShopItem('booster_multiplier_stack', 'Multiplier Stack', 
                    'Stack multiple multipliers (XP + Quality + Stats)', 1500,
                    'power_up', 'boosts', '📈💎', 'legendary', {'type': 'multiplier_stack', 'stack_count': 'random(2, 4)'}),
            ShopItem('booster_time_warp', 'Time Warp Booster', 
                    'Speed up video generation by 50%', 800,
                    'power_up', 'boosts', '⏰⚡', 'rare', {'type': 'time_warp', 'generation_speed': 1.5, 'duration': 3600}),
            ShopItem('booster_creative_surge', 'Creative Surge', 
                    'Enhanced AI prompts for better video quality', 900,
                    'power_up', 'boosts', '🧠✨', 'epic', {'type': 'creative_surge', 'prompt_enhancement': 0.3, 'duration': 7200}),
            ShopItem('booster_lucky_draw', 'Lucky Draw Booster', 
                    'Random reward from all booster types', 600,
                    'power_up', 'boosts', '🍀🎁', 'rare', {'type': 'lucky_draw', 'reward_pool': 'all_boosters'}),
            ShopItem('booster_combo', 'Combo Booster', 
                    'Multiple random effects combined (3-5 effects)', 2000,
                    'power_up', 'boosts', '💥💎', 'legendary', {'type': 'combo', 'effect_count': 'random(3, 5)'}),
        ]
        
        # Cosmetic Items
        cosmetics = [
            ShopItem('badge_legendary', 'Legendary Badge', 'Rare legendary badge', 1000,
                    'cosmetic', 'badges', '💎', 'legendary'),
            ShopItem('title_custom', 'Custom Title', 'Create custom player title', 800,
                    'cosmetic', 'titles', '👑', 'epic'),
            ShopItem('profile_frame', 'Gold Frame', 'Gold profile frame', 600,
                    'cosmetic', 'frames', '🖼️', 'rare'),
        ]
        
        # Currency Packs
        currency_packs = [
            ShopItem('currency_100', '100 Coins', 'Get 100 game coins', 100,
                    'currency', 'currency', '🪙', 'common', {'currency': 100}),
            ShopItem('currency_500', '500 Coins', 'Get 500 game coins (bonus: +50)', 450,
                    'currency', 'currency', '🪙🪙', 'common', {'currency': 550}),
            ShopItem('currency_1000', '1000 Coins', 'Get 1000 game coins (bonus: +200)', 800,
                    'currency', 'currency', '🪙🪙🪙', 'rare', {'currency': 1200}),
        ]
        
        # Add all items
        for item in themes + power_ups + random_boosters + cosmetics + currency_packs:
            self.items[item.id] = item
    
    def get_shop_items(self, category: str = None) -> List[Dict]:
        """Get shop items, optionally filtered by category"""
        items = list(self.items.values())
        if category:
            items = [i for i in items if i.category == category]
        return [i.to_dict() for i in items if i.available]
    
    def get_user_currency(self, user_id: str) -> int:
        """Get user's currency balance"""
        return self.user_currency.get(user_id, 0)
    
    def add_currency(self, user_id: str, amount: int) -> Dict[str, Any]:
        """Add currency to user"""
        self.user_currency[user_id] = self.user_currency.get(user_id, 0) + amount
        return {
            'success': True,
            'new_balance': self.user_currency[user_id]
        }
    
    def purchase_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Purchase an item from shop"""
        import random
        
        item = self.items.get(item_id)
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        if not item.available:
            return {'success': False, 'error': 'Item not available'}
        
        if item.stock >= 0 and item.purchased_count >= item.stock:
            return {'success': False, 'error': 'Item out of stock'}
        
        user_currency = self.get_user_currency(user_id)
        if user_currency < item.price:
            return {'success': False, 'error': 'Insufficient currency'}
        
        # Check if already owned (for non-consumable items)
        if item.type in ['theme', 'cosmetic'] and item_id in self.user_inventory[user_id]:
            return {'success': False, 'error': 'Item already owned'}
        
        # Deduct currency
        self.user_currency[user_id] = user_currency - item.price
        
        # Handle random boosters
        actual_effects = item.effects.copy() if item.effects else {}
        random_reward = None
        
        if item.effects and item.effects.get('type') == 'random_booster':
            rarity = item.effects.get('rarity', 'common')
            random_reward = self._generate_random_booster_reward(rarity)
            actual_effects = random_reward['effects']
        
        # Add to inventory
        self.user_inventory[user_id].append(item_id)
        item.purchased_count += 1
        
        # Record purchase
        purchase = {
            'item_id': item_id,
            'item_name': item.name,
            'price': item.price,
            'purchased_at': datetime.utcnow().isoformat(),
            'random_reward': random_reward
        }
        self.purchase_history[user_id].append(purchase)
        
        return {
            'success': True,
            'item': item.to_dict(),
            'new_balance': self.user_currency[user_id],
            'effects': actual_effects,
            'random_reward': random_reward
        }
    
    def _generate_random_booster_reward(self, rarity: str) -> Dict[str, Any]:
        """Generate random reward from booster pack - Enhanced with new boosters"""
        import random
        
        # Try to use enhanced random booster system if available
        try:
            from backend.services.random_booster_system import random_booster_system
            result = random_booster_system.generate_random_booster(rarity, 'shop_user')
            if result.get('success'):
                booster = result.get('booster', {})
                return {
                    'name': booster.get('name', 'Random Booster'),
                    'effects': booster.get('effects', {}),
                    'icon': '🎁',
                    'booster_id': booster.get('booster_id')
                }
        except ImportError:
            pass  # Fall back to default system
        
        # Define possible rewards by rarity (fallback)
        rewards = {
            'common': [
                {'name': 'XP Boost (30min)', 'effects': {'xp_multiplier': 1.5, 'duration': 1800}, 'icon': '⚡'},
                {'name': '50 Coins', 'effects': {'currency': 50}, 'icon': '🪙'},
                {'name': 'Stat Point', 'effects': {'stat_points': 1}, 'icon': '📊'},
                {'name': 'Energy Drink', 'effects': {'energy': 50}, 'icon': '🥤'},
                {'name': 'Small Quality Boost', 'effects': {'quality_boost': 0.05, 'duration': 3600}, 'icon': '⭐'},
            ],
            'rare': [
                {'name': 'XP Boost (2h)', 'effects': {'xp_multiplier': 2.0, 'duration': 7200}, 'icon': '⚡⚡'},
                {'name': '200 Coins', 'effects': {'currency': 200}, 'icon': '🪙🪙'},
                {'name': 'Quality Boost', 'effects': {'quality_boost': random.uniform(0.1, 0.2), 'duration': 7200}, 'icon': '⭐'},
                {'name': 'Time Warp', 'effects': {'generation_speed': 1.5, 'duration': 3600}, 'icon': '⏰'},
                {'name': 'Luck Charm', 'effects': {'luck_multiplier': 2.0, 'duration': 3600}, 'icon': '🍀'},
            ],
            'epic': [
                {'name': 'XP Boost (6h)', 'effects': {'xp_multiplier': 2.5, 'duration': 21600}, 'icon': '⚡⚡⚡'},
                {'name': '500 Coins', 'effects': {'currency': 500}, 'icon': '🪙🪙🪙'},
                {'name': 'Video Quality Boost', 'effects': {'quality_boost': random.uniform(0.2, 0.3), 'duration': 10800}, 'icon': '🎬⭐'},
                {'name': 'Creative Surge', 'effects': {'prompt_enhancement': 0.3, 'quality_boost': 0.1, 'duration': 10800}, 'icon': '🧠✨'},
                {'name': 'Multiplier Stack', 'effects': {'xp_multiplier': 1.5, 'quality_boost': 0.15, 'stat_points': 2, 'duration': 7200}, 'icon': '📈'},
                {'name': 'Theme Unlock Chance', 'effects': {'theme_unlock_chance': 0.3}, 'icon': '🎨'},
            ],
            'legendary': [
                {'name': 'XP Boost (24h)', 'effects': {'xp_multiplier': 3.0, 'duration': 86400}, 'icon': '⚡⚡⚡⚡'},
                {'name': '1000 Coins', 'effects': {'currency': 1000}, 'icon': '🪙🪙🪙🪙'},
                {'name': 'Legendary Quality Boost', 'effects': {'quality_bonus': 0.4}, 'icon': '⭐⭐⭐'},
                {'name': 'Ultimate Mind Magi', 'effects': {'creativity_boost': 0.35, 'focus_boost': 0.4, 'xp_multiplier': 1.5, 'duration': 10800}, 'icon': '🧠💎'},
            ]
        }
        
        available_rewards = rewards.get(rarity, rewards['common'])
        reward = random.choice(available_rewards)
        
        return {
            'name': reward['name'],
            'icon': reward['icon'],
            'effects': reward['effects'],
            'rarity': rarity
        }
    
    def get_user_inventory(self, user_id: str) -> List[Dict]:
        """Get user's inventory"""
        inventory = []
        for item_id in self.user_inventory[user_id]:
            item = self.items.get(item_id)
            if item:
                inventory.append(item.to_dict())
        return inventory
    
    def use_item(self, user_id: str, item_id: str) -> Dict[str, Any]:
        """Use a consumable item"""
        if item_id not in self.user_inventory[user_id]:
            return {'success': False, 'error': 'Item not in inventory'}
        
        item = self.items.get(item_id)
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        # Check if consumable
        if item.type not in ['power_up', 'currency']:
            return {'success': False, 'error': 'Item is not consumable'}
        
        # Remove from inventory if consumable
        if item.type == 'power_up':
            self.user_inventory[user_id].remove(item_id)
        
        return {
            'success': True,
            'effects': item.effects,
            'message': f'Used {item.name}'
        }
    
    def get_purchase_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get purchase history"""
        history = self.purchase_history.get(user_id, [])
        history.sort(key=lambda p: p['purchased_at'], reverse=True)
        return history[:limit]


# Global instance
game_shop = GameShop()

