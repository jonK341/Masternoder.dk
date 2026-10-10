"""
Shop System v2.0
Enhanced shop with new boosters, game time, artifacts, and tech intelligence
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random
import time

# Import intelligence systems
try:
    from backend.services.battle_intelligence_system import BattleIntelligenceSystem
    from backend.services.point_connection_system import point_connection
except ImportError:
    BattleIntelligenceSystem = None
    point_connection = None


class ShopV2System:
    """
    Enhanced shop system v2.0 with intelligence and new items
    """
    
    def __init__(self):
        self.items = {}
        self.boosters = {}
        self.artifacts = {}
        self.game_time_items = {}
        self.user_inventory = defaultdict(dict)  # user_id -> {item_id: quantity}
        self.purchase_history = defaultdict(list)  # user_id -> [purchases]
        self.intelligence = BattleIntelligenceSystem() if BattleIntelligenceSystem else None
        self._initialize_items()
        self._initialize_boosters()
        self._initialize_artifacts()
        self._initialize_game_time_items()
    
    def _initialize_items(self):
        """Initialize shop items"""
        self.items = {
            'energy_potion': {
                'id': 'energy_potion',
                'name': 'Energy Potion',
                'description': 'Restore 100 energy instantly',
                'price': 200,
                'type': 'consumable',
                'rarity': 'common',
                'icon': '⚡',
                'effect': {'energy': 100}
            },
            'lucky_charm': {
                'id': 'lucky_charm',
                'name': 'Lucky Charm',
                'description': '+10% luck for 1 hour',
                'price': 300,
                'type': 'consumable',
                'rarity': 'rare',
                'icon': '🍀',
                'effect': {'luck_boost': 0.1, 'duration': 3600}
            },
            'quality_enhancer': {
                'id': 'quality_enhancer',
                'name': 'Quality Enhancer',
                'description': '+15% quality for next video',
                'price': 400,
                'type': 'consumable',
                'rarity': 'epic',
                'icon': '✨',
                'effect': {'quality_boost': 0.15}
            },
            'speed_boost': {
                'id': 'speed_boost',
                'name': 'Speed Boost',
                'description': '+20% speed for 30 minutes',
                'price': 250,
                'type': 'consumable',
                'rarity': 'rare',
                'icon': '⚡',
                'effect': {'speed_boost': 0.2, 'duration': 1800}
            }
        }
    
    def _initialize_boosters(self):
        """Initialize new boosters v2.0"""
        self.boosters = {
            # Game Time Boosters
            'time_accelerator': {
                'id': 'time_accelerator',
                'name': 'Time Accelerator',
                'description': 'Speed up game time by 2x for 1 hour',
                'price': 500,
                'type': 'booster',
                'rarity': 'epic',
                'icon': '⏰',
                'effect': {'time_multiplier': 2.0, 'duration': 3600}
            },
            'time_freeze': {
                'id': 'time_freeze',
                'name': 'Time Freeze',
                'description': 'Freeze timers for 30 minutes',
                'price': 800,
                'type': 'booster',
                'rarity': 'legendary',
                'icon': '❄️',
                'effect': {'time_freeze': True, 'duration': 1800}
            },
            'time_warp': {
                'id': 'time_warp',
                'name': 'Time Warp',
                'description': 'Skip waiting times for 2 hours',
                'price': 1200,
                'type': 'booster',
                'rarity': 'legendary',
                'icon': '🌀',
                'effect': {'skip_waiting': True, 'duration': 7200}
            },
            'time_multiplier': {
                'id': 'time_multiplier',
                'name': 'Time Multiplier',
                'description': '3x time speed for 3 hours',
                'price': 1500,
                'type': 'booster',
                'rarity': 'mythic',
                'icon': '⏱️',
                'effect': {'time_multiplier': 3.0, 'duration': 10800}
            },
            
            # Power Boosters
            'xp_multiplier': {
                'id': 'xp_multiplier',
                'name': 'XP Multiplier Booster',
                'description': '2x XP for 1 hour',
                'price': 600,
                'type': 'booster',
                'rarity': 'epic',
                'icon': '⭐',
                'effect': {'xp_multiplier': 2.0, 'duration': 3600}
            },
            'point_doubler': {
                'id': 'point_doubler',
                'name': 'Point Doubler',
                'description': 'Double all points for 30 minutes',
                'price': 800,
                'type': 'booster',
                'rarity': 'legendary',
                'icon': '💎',
                'effect': {'point_multiplier': 2.0, 'duration': 1800}
            },
            'streak_protector': {
                'id': 'streak_protector',
                'name': 'Streak Protector',
                'description': 'Protect streak from breaking once',
                'price': 1000,
                'type': 'booster',
                'rarity': 'legendary',
                'icon': '🛡️',
                'effect': {'streak_protection': 1}
            },
            'victory_guarantee': {
                'id': 'victory_guarantee',
                'name': 'Victory Guarantee',
                'description': 'Guaranteed win in next battle',
                'price': 2000,
                'type': 'booster',
                'rarity': 'mythic',
                'icon': '👑',
                'effect': {'guaranteed_win': True}
            },
            
            # Artifact Boosters
            'artifact_discovery': {
                'id': 'artifact_discovery',
                'name': 'Artifact Discovery',
                'description': '50% chance to discover artifact',
                'price': 1500,
                'type': 'booster',
                'rarity': 'legendary',
                'icon': '🔍',
                'effect': {'artifact_chance': 0.5}
            },
            'artifact_upgrade': {
                'id': 'artifact_upgrade',
                'name': 'Artifact Upgrade',
                'description': 'Upgrade existing artifact',
                'price': 2000,
                'type': 'booster',
                'rarity': 'mythic',
                'icon': '⬆️',
                'effect': {'artifact_upgrade': True}
            },
            'artifact_fusion': {
                'id': 'artifact_fusion',
                'name': 'Artifact Fusion',
                'description': 'Combine two artifacts',
                'price': 3000,
                'type': 'booster',
                'rarity': 'mythic',
                'icon': '🔗',
                'effect': {'artifact_fusion': True}
            }
        }
    
    def _initialize_artifacts(self):
        """Initialize new artifacts v2.0"""
        self.artifacts = {
            # Legendary Artifacts
            'champions_crown': {
                'id': 'champions_crown',
                'name': "Champion's Crown",
                'description': '+50% to all points, +25% win rate',
                'price': 5000,
                'type': 'artifact',
                'rarity': 'legendary',
                'icon': '👑',
                'effect': {'point_multiplier': 1.5, 'win_rate_boost': 0.25},
                'power': 200
            },
            'time_masters_hourglass': {
                'id': 'time_masters_hourglass',
                'name': "Time Master's Hourglass",
                'description': 'Time bonuses, speed boosts',
                'price': 4500,
                'type': 'artifact',
                'rarity': 'legendary',
                'icon': '⏳',
                'effect': {'time_bonus': 0.3, 'speed_boost': 0.2},
                'power': 180
            },
            'point_collectors_gem': {
                'id': 'point_collectors_gem',
                'name': "Point Collector's Gem",
                'description': '+30% point collection rate',
                'price': 4000,
                'type': 'artifact',
                'rarity': 'legendary',
                'icon': '💎',
                'effect': {'collection_rate': 1.3},
                'power': 150
            },
            'battle_masters_sword': {
                'id': 'battle_masters_sword',
                'name': "Battle Master's Sword",
                'description': '+40% battle points, +20% victory rate',
                'price': 5500,
                'type': 'artifact',
                'rarity': 'legendary',
                'icon': '⚔️',
                'effect': {'battle_points_multiplier': 1.4, 'victory_rate': 0.2},
                'power': 220
            },
            
            # Mythic Artifacts
            'unified_point_matrix': {
                'id': 'unified_point_matrix',
                'name': 'Unified Point Matrix',
                'description': 'Connects all point systems, +100% efficiency',
                'price': 10000,
                'type': 'artifact',
                'rarity': 'mythic',
                'icon': '🔷',
                'effect': {'point_efficiency': 2.0, 'unified_bonus': 1.0},
                'power': 500
            },
            'intelligence_core': {
                'id': 'intelligence_core',
                'name': 'Intelligence Core',
                'description': 'AI-powered recommendations, +50% intelligence',
                'price': 8000,
                'type': 'artifact',
                'rarity': 'mythic',
                'icon': '🧠',
                'effect': {'intelligence_boost': 1.5, 'ai_power': 1.3},
                'power': 400
            },
            'network_nexus': {
                'id': 'network_nexus',
                'name': 'Network Nexus',
                'description': 'Social network bonuses, +30% social points',
                'price': 7500,
                'type': 'artifact',
                'rarity': 'mythic',
                'icon': '🌐',
                'effect': {'social_points_multiplier': 1.3, 'network_bonus': 0.2},
                'power': 350
            }
        }
    
    def _initialize_game_time_items(self):
        """Initialize game time items"""
        self.game_time_items = {
            'game_time_1h': {
                'id': 'game_time_1h',
                'name': 'Game Time (1 Hour)',
                'description': 'Add 1 hour of game time',
                'price': 300,
                'type': 'game_time',
                'rarity': 'common',
                'icon': '⏰',
                'effect': {'game_time': 3600}
            },
            'game_time_3h': {
                'id': 'game_time_3h',
                'name': 'Game Time (3 Hours)',
                'description': 'Add 3 hours of game time',
                'price': 800,
                'type': 'game_time',
                'rarity': 'rare',
                'icon': '⏰',
                'effect': {'game_time': 10800}
            },
            'game_time_24h': {
                'id': 'game_time_24h',
                'name': 'Game Time (24 Hours)',
                'description': 'Add 24 hours of game time',
                'price': 5000,
                'type': 'game_time',
                'rarity': 'epic',
                'icon': '⏰',
                'effect': {'game_time': 86400}
            }
        }
    
    def get_shop_intelligence(self, user_id: str) -> Dict[str, Any]:
        """
        Get AI-powered shop recommendations
        
        Returns:
            Dictionary with intelligent recommendations
        """
        recommendations = {
            'recommended_items': [],
            'best_value': [],
            'personalized_suggestions': [],
            'bundle_suggestions': []
        }
        
        # Get user stats
        if point_connection:
            try:
                all_points = point_connection.get_all_connected_points(user_id)
                points_data = all_points.get('all_points', {})
                
                # Recommend based on user needs
                if points_data.get('battle_points', 0) < 100:
                    recommendations['recommended_items'].append({
                        'item': 'battle_masters_sword',
                        'reason': 'Low battle points - boost battle performance',
                        'priority': 'high'
                    })
                
                if points_data.get('xp', 0) < 500:
                    recommendations['recommended_items'].append({
                        'item': 'xp_multiplier',
                        'reason': 'Low XP - accelerate leveling',
                        'priority': 'medium'
                    })
                
                if points_data.get('activity_points', 0) < 200:
                    recommendations['recommended_items'].append({
                        'item': 'point_doubler',
                        'reason': 'Low activity - double your points',
                        'priority': 'high'
                    })
            except:
                pass
        
        # Best value items
        recommendations['best_value'] = [
            {'item': 'energy_potion', 'value_score': 0.5, 'reason': 'High utility, low cost'},
            {'item': 'lucky_charm', 'value_score': 0.4, 'reason': 'Good luck boost'},
            {'item': 'time_accelerator', 'value_score': 0.6, 'reason': 'Great time value'}
        ]
        
        # Bundle suggestions
        recommendations['bundle_suggestions'] = [
            {
                'name': 'Starter Pack',
                'items': ['energy_potion', 'lucky_charm', 'speed_boost'],
                'total_price': 750,
                'discount': 100,
                'savings': '13%'
            },
            {
                'name': 'Power Pack',
                'items': ['xp_multiplier', 'point_doubler', 'time_accelerator'],
                'total_price': 1900,
                'discount': 300,
                'savings': '16%'
            }
        ]
        
        return recommendations
    
    def purchase_item(self, user_id: str, item_id: str, quantity: int = 1) -> Dict[str, Any]:
        """
        Purchase item from shop
        
        Returns:
            Purchase result with points awarded
        """
        # Find item in all categories
        item = None
        item_category = None
        
        if item_id in self.items:
            item = self.items[item_id]
            item_category = 'items'
        elif item_id in self.boosters:
            item = self.boosters[item_id]
            item_category = 'boosters'
        elif item_id in self.artifacts:
            item = self.artifacts[item_id]
            item_category = 'artifacts'
        elif item_id in self.game_time_items:
            item = self.game_time_items[item_id]
            item_category = 'game_time'
        
        if not item:
            return {'success': False, 'error': 'Item not found'}
        
        total_price = item['price'] * quantity
        
        # Award shop points (1 point per 10 coins spent)
        shop_points = total_price // 10
        first_purchase_bonus = 0
        
        if user_id not in self.purchase_history or len(self.purchase_history[user_id]) == 0:
            first_purchase_bonus = 50
        
        bulk_bonus = 25 if quantity >= 5 else 0
        
        total_shop_points = shop_points + first_purchase_bonus + bulk_bonus
        
        # Add to inventory
        if item_id not in self.user_inventory[user_id]:
            self.user_inventory[user_id][item_id] = 0
        self.user_inventory[user_id][item_id] += quantity
        
        # Record purchase
        purchase = {
            'item_id': item_id,
            'item_name': item['name'],
            'quantity': quantity,
            'price': total_price,
            'shop_points': total_shop_points,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.purchase_history[user_id].append(purchase)
        
        # Award points via unified system
        if point_connection:
            try:
                point_connection.ensure_point_counting(user_id, 'shop_points', total_shop_points, 'shop_purchase')
            except:
                pass
        
        return {
            'success': True,
            'item': item,
            'quantity': quantity,
            'total_price': total_price,
            'shop_points_awarded': total_shop_points,
            'inventory': self.user_inventory[user_id]
        }
    
    def get_all_items(self) -> Dict[str, Any]:
        """Get all shop items"""
        return {
            'items': list(self.items.values()),
            'boosters': list(self.boosters.values()),
            'artifacts': list(self.artifacts.values()),
            'game_time_items': list(self.game_time_items.values()),
            'total_items': len(self.items) + len(self.boosters) + len(self.artifacts) + len(self.game_time_items)
        }


# Global instance
shop_v2 = ShopV2System()

