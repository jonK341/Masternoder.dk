"""
Booster Pack System
Different forms: gametime, token, trophy, XP points, random celebration goodies
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import json


class BoosterPack:
    """Base booster pack class"""
    
    def __init__(self, pack_type: str, rarity: str = 'common'):
        self.pack_type = pack_type
        self.rarity = rarity
        self.contents = []
        self.opened_at = None
    
    def generate_contents(self) -> List[Dict[str, Any]]:
        """Generate pack contents based on type and rarity"""
        contents = []
        
        if self.pack_type == 'gametime':
            contents.extend(self._generate_gametime_contents())
        elif self.pack_type == 'token':
            contents.extend(self._generate_token_contents())
        elif self.pack_type == 'trophy':
            contents.extend(self._generate_trophy_contents())
        elif self.pack_type == 'xp':
            contents.extend(self._generate_xp_contents())
        elif self.pack_type == 'celebration':
            contents.extend(self._generate_celebration_contents())
        elif self.pack_type == 'premium':
            contents.extend(self._generate_premium_contents())
        
        # Add random celebration goodies
        contents.extend(self._add_celebration_goodies())
        
        self.contents = contents
        return contents
    
    def _generate_gametime_contents(self) -> List[Dict[str, Any]]:
        """Generate gametime booster contents"""
        rarity_multipliers = {
            'common': 1,
            'rare': 2,
            'epic': 3,
            'legendary': 5
        }
        multiplier = rarity_multipliers.get(self.rarity, 1)
        
        return [
            {'type': 'gametime_boost', 'duration': 3600 * multiplier, 'description': f'{multiplier} hour gametime boost'},
            {'type': 'speed_boost', 'duration': 1800 * multiplier, 'description': f'{multiplier * 0.5} hour speed boost'},
            {'type': 'quality_boost', 'duration': 3600 * multiplier, 'description': f'{multiplier} hour quality boost'}
        ]
    
    def _generate_token_contents(self) -> List[Dict[str, Any]]:
        """Generate token booster contents"""
        rarity_amounts = {
            'common': {'coins': 100, 'premium_coins': 10},
            'rare': {'coins': 500, 'premium_coins': 50},
            'epic': {'coins': 1000, 'premium_coins': 100},
            'legendary': {'coins': 5000, 'premium_coins': 500}
        }
        amounts = rarity_amounts.get(self.rarity, {'coins': 100, 'premium_coins': 10})
        
        return [
            {'type': 'coins', 'amount': amounts['coins'], 'description': f'{amounts["coins"]} coins'},
            {'type': 'premium_coins', 'amount': amounts['premium_coins'], 'description': f'{amounts["premium_coins"]} premium coins'}
        ]
    
    def _generate_trophy_contents(self) -> List[Dict[str, Any]]:
        """Generate trophy booster contents"""
        trophy_types = {
            'common': ['bronze_badge', 'participation_medal'],
            'rare': ['silver_badge', 'achievement_medal'],
            'epic': ['gold_badge', 'excellence_medal'],
            'legendary': ['platinum_badge', 'legendary_medal', 'exclusive_trophy']
        }
        
        trophies = trophy_types.get(self.rarity, ['bronze_badge'])
        selected = random.sample(trophies, min(2, len(trophies)))
        
        return [
            {'type': 'trophy', 'trophy_id': trophy, 'description': f'{trophy.replace("_", " ").title()}'}
            for trophy in selected
        ]
    
    def _generate_xp_contents(self) -> List[Dict[str, Any]]:
        """Generate XP booster contents"""
        rarity_xp = {
            'common': 500,
            'rare': 2000,
            'epic': 5000,
            'legendary': 20000
        }
        xp_amount = rarity_xp.get(self.rarity, 500)
        
        return [
            {'type': 'xp', 'amount': xp_amount, 'description': f'{xp_amount} XP points'},
            {'type': 'xp_boost', 'multiplier': 1.5, 'duration': 3600, 'description': '1.5x XP boost for 1 hour'}
        ]
    
    def _generate_celebration_contents(self) -> List[Dict[str, Any]]:
        """Generate celebration booster contents"""
        return [
            {'type': 'celebration_effect', 'effect': 'confetti', 'duration': 60, 'description': 'Confetti celebration'},
            {'type': 'celebration_theme', 'theme': 'party', 'duration': 3600, 'description': 'Party theme for 1 hour'},
            {'type': 'celebration_sound', 'sound': 'victory', 'description': 'Victory sound effect'},
            {'type': 'celebration_animation', 'animation': 'fireworks', 'description': 'Fireworks animation'}
        ]
    
    def _generate_premium_contents(self) -> List[Dict[str, Any]]:
        """Generate premium booster contents"""
        return [
            {'type': 'premium_coins', 'amount': random.randint(50, 200), 'description': 'Premium coins'},
            {'type': 'exclusive_theme', 'theme': f'exclusive_{random.randint(1, 5)}', 'description': 'Exclusive theme'},
            {'type': 'premium_power_up', 'power_up': random.choice(['quality_boost', 'speed_boost', 'extra_clips']), 'description': 'Premium power-up'},
            {'type': 'subscription_discount', 'discount': 0.1, 'description': '10% subscription discount'}
        ]
    
    def _add_celebration_goodies(self) -> List[Dict[str, Any]]:
        """Add random celebration goodies to any pack"""
        goodies = [
            {'type': 'celebration_emoji', 'emoji': random.choice(['🎉', '🎊', '🎈', '🎁', '⭐', '✨', '🌟', '💫']), 'description': 'Celebration emoji'},
            {'type': 'celebration_message', 'message': random.choice(['Amazing!', 'Fantastic!', 'Incredible!', 'Outstanding!']), 'description': 'Celebration message'},
            {'type': 'celebration_color', 'color': random.choice(['gold', 'silver', 'rainbow']), 'description': 'Special color effect'}
        ]
        
        # Add 1-3 random goodies
        num_goodies = random.randint(1, 3)
        return random.sample(goodies, min(num_goodies, len(goodies)))


class BoosterPackSystem:
    """System for managing booster packs"""
    
    def __init__(self):
        self.pack_types = ['gametime', 'token', 'trophy', 'xp', 'celebration', 'premium']
        self.rarities = ['common', 'rare', 'epic', 'legendary']
        self.pack_prices = {
            'gametime': {'coins': 500, 'premium_coins': 50},
            'token': {'coins': 300, 'premium_coins': 30},
            'trophy': {'coins': 1000, 'premium_coins': 100},
            'xp': {'coins': 400, 'premium_coins': 40},
            'celebration': {'coins': 200, 'premium_coins': 20},
            'premium': {'premium_coins': 100}
        }
    
    def create_pack(self, pack_type: str, rarity: str = None) -> BoosterPack:
        """Create a booster pack"""
        if rarity is None:
            rarity = self._determine_rarity()
        
        pack = BoosterPack(pack_type, rarity)
        pack.generate_contents()
        return pack
    
    def _determine_rarity(self) -> str:
        """Determine pack rarity based on probability"""
        rand = random.random()
        if rand < 0.5:
            return 'common'
        elif rand < 0.8:
            return 'rare'
        elif rand < 0.95:
            return 'epic'
        else:
            return 'legendary'
    
    def open_pack(self, pack: BoosterPack) -> Dict[str, Any]:
        """Open a booster pack and return contents"""
        pack.opened_at = datetime.now()
        
        return {
            'pack_type': pack.pack_type,
            'rarity': pack.rarity,
            'contents': pack.contents,
            'opened_at': pack.opened_at.isoformat()
        }
    
    def get_pack_price(self, pack_type: str) -> Dict[str, int]:
        """Get price for a pack type"""
        return self.pack_prices.get(pack_type, {'coins': 500})
    
    def purchase_pack(self, pack_type: str, payment_method: str = 'coins') -> Optional[BoosterPack]:
        """Purchase a booster pack"""
        price = self.get_pack_price(pack_type)
        
        if payment_method not in price:
            return None
        
        # In production, this would check user balance and deduct
        # For now, just create the pack
        pack = self.create_pack(pack_type)
        return pack


class InfiniteLevelingSystem:
    """Infinite leveling system to ensure user time spent on resources"""
    
    def __init__(self):
        self.base_xp = 1000
        self.xp_multiplier = 1.5
        self.max_level = None  # Infinite
    
    def calculate_xp_for_level(self, level: int) -> int:
        """Calculate XP needed for a specific level"""
        if level <= 1:
            return 0
        
        total_xp = 0
        for i in range(1, level):
            total_xp += int(self.base_xp * (self.xp_multiplier ** (i - 1)))
        
        return total_xp
    
    def calculate_level_from_xp(self, total_xp: int) -> int:
        """Calculate level from total XP"""
        level = 1
        xp_needed = 0
        
        while xp_needed <= total_xp:
            xp_for_next = int(self.base_xp * (self.xp_multiplier ** (level - 1)))
            if xp_needed + xp_for_next > total_xp:
                break
            xp_needed += xp_for_next
            level += 1
        
        return level
    
    def get_xp_progress(self, current_xp: int, current_level: int) -> Dict[str, Any]:
        """Get XP progress for current level"""
        xp_for_current = self.calculate_xp_for_level(current_level)
        xp_for_next = self.calculate_xp_for_level(current_level + 1)
        xp_needed_for_next = xp_for_next - xp_for_current
        xp_in_current_level = current_xp - xp_for_current
        
        progress_percent = (xp_in_current_level / xp_needed_for_next * 100) if xp_needed_for_next > 0 else 100
        
        return {
            'current_level': current_level,
            'current_xp': current_xp,
            'xp_for_current_level': xp_in_current_level,
            'xp_needed_for_next': xp_needed_for_next,
            'xp_for_next_level': xp_for_next,
            'progress_percent': progress_percent,
            'next_level': current_level + 1
        }
    
    def get_level_rewards(self, level: int) -> Dict[str, Any]:
        """Get rewards for reaching a level"""
        # Every 5 levels: bigger rewards
        # Every 10 levels: major rewards
        # Every 25 levels: legendary rewards
        # Every 50 levels: epic rewards
        
        rewards = {
            'coins': level * 10,
            'premium_coins': max(0, (level // 5) * 5),
            'xp': 0  # Already leveled up
        }
        
        if level % 5 == 0:
            rewards['power_up'] = 'quality_boost'
            rewards['coins'] += 500
        
        if level % 10 == 0:
            rewards['theme'] = f'exclusive_theme_{level // 10}'
            rewards['premium_coins'] += 50
            rewards['title'] = f'Level {level} Master'
        
        if level % 25 == 0:
            rewards['exclusive_feature'] = f'feature_level_{level}'
            rewards['premium_coins'] += 200
            rewards['badge'] = f'level_{level}_badge'
        
        if level % 50 == 0:
            rewards['subscription_discount'] = 0.15
            rewards['premium_coins'] += 500
            rewards['legendary_badge'] = True
        
        return rewards


class StatsCounter:
    """Counter for all attributes and stats"""
    
    def __init__(self):
        self.stats = {
            'generation': {
                'total_generations': 0,
                'successful_generations': 0,
                'failed_generations': 0,
                'total_duration': 0,
                'average_quality': 0.0,
                'total_clips': 0,
                'themes_used': {},
                'providers_used': {}
            },
            'leveling': {
                'current_level': 1,
                'total_xp': 0,
                'xp_from_generations': 0,
                'xp_from_quests': 0,
                'xp_from_achievements': 0,
                'level_ups': 0
            },
            'monetization': {
                'total_spent': 0.0,
                'purchases_count': 0,
                'subscription_months': 0,
                'booster_packs_opened': 0,
                'coins_earned': 0,
                'coins_spent': 0,
                'premium_coins_earned': 0,
                'premium_coins_spent': 0
            },
            'engagement': {
                'total_sessions': 0,
                'total_time_spent': 0,
                'days_active': 0,
                'streak_days': 0,
                'last_active': None
            },
            'game': {
                'quests_completed': 0,
                'achievements_unlocked': 0,
                'trophies_earned': 0,
                'leaderboard_rank': 0,
                'presents_opened': 0
            },
            'attributes': {
                'creativity': 0,
                'quality_focus': 0,
                'speed': 0,
                'consistency': 0,
                'innovation': 0,
                'community': 0
            }
        }
    
    def update_generation_stats(self, generation_data: Dict[str, Any]):
        """Update generation statistics"""
        stats = self.stats['generation']
        
        stats['total_generations'] += 1
        
        if generation_data.get('status') == 'completed':
            stats['successful_generations'] += 1
        else:
            stats['failed_generations'] += 1
        
        if generation_data.get('duration'):
            stats['total_duration'] += generation_data['duration']
        
        if generation_data.get('quality_score'):
            current_avg = stats['average_quality']
            total = stats['successful_generations']
            stats['average_quality'] = ((current_avg * (total - 1)) + generation_data['quality_score']) / total
        
        if generation_data.get('clips'):
            stats['total_clips'] += len(generation_data['clips'])
        
        if generation_data.get('theme'):
            theme = generation_data['theme']
            stats['themes_used'][theme] = stats['themes_used'].get(theme, 0) + 1
        
        if generation_data.get('provider'):
            provider = generation_data['provider']
            stats['providers_used'][provider] = stats['providers_used'].get(provider, 0) + 1
    
    def update_leveling_stats(self, xp_gained: int, source: str):
        """Update leveling statistics"""
        stats = self.stats['leveling']
        
        stats['total_xp'] += xp_gained
        
        if source == 'generation':
            stats['xp_from_generations'] += xp_gained
        elif source == 'quest':
            stats['xp_from_quests'] += xp_gained
        elif source == 'achievement':
            stats['xp_from_achievements'] += xp_gained
        
        # Check for level up
        from src.services.monetization.booster_pack_system import InfiniteLevelingSystem
        leveling_system = InfiniteLevelingSystem()
        new_level = leveling_system.calculate_level_from_xp(stats['total_xp'])
        
        if new_level > stats['current_level']:
            stats['level_ups'] += 1
            stats['current_level'] = new_level
    
    def update_monetization_stats(self, purchase_data: Dict[str, Any]):
        """Update monetization statistics"""
        stats = self.stats['monetization']
        
        if purchase_data.get('amount'):
            stats['total_spent'] += purchase_data['amount']
        
        stats['purchases_count'] += 1
        
        if purchase_data.get('type') == 'subscription':
            stats['subscription_months'] += purchase_data.get('months', 1)
        
        if purchase_data.get('type') == 'booster_pack':
            stats['booster_packs_opened'] += 1
        
        if purchase_data.get('coins_earned'):
            stats['coins_earned'] += purchase_data['coins_earned']
        
        if purchase_data.get('coins_spent'):
            stats['coins_spent'] += purchase_data['coins_spent']
        
        if purchase_data.get('premium_coins_earned'):
            stats['premium_coins_earned'] += purchase_data['premium_coins_earned']
        
        if purchase_data.get('premium_coins_spent'):
            stats['premium_coins_spent'] += purchase_data['premium_coins_spent']
    
    def update_engagement_stats(self, session_data: Dict[str, Any]):
        """Update engagement statistics"""
        stats = self.stats['engagement']
        
        stats['total_sessions'] += 1
        
        if session_data.get('duration'):
            stats['total_time_spent'] += session_data['duration']
        
        if session_data.get('is_new_day'):
            stats['days_active'] += 1
        
        if session_data.get('maintains_streak'):
            stats['streak_days'] += 1
        
        stats['last_active'] = datetime.now().isoformat()
    
    def update_game_stats(self, game_data: Dict[str, Any]):
        """Update game statistics"""
        stats = self.stats['game']
        
        if game_data.get('quest_completed'):
            stats['quests_completed'] += 1
        
        if game_data.get('achievement_unlocked'):
            stats['achievements_unlocked'] += 1
        
        if game_data.get('trophy_earned'):
            stats['trophies_earned'] += 1
        
        if game_data.get('leaderboard_rank'):
            stats['leaderboard_rank'] = game_data['leaderboard_rank']
        
        if game_data.get('present_opened'):
            stats['presents_opened'] += 1
    
    def update_attributes(self, attribute_updates: Dict[str, int]):
        """Update user attributes"""
        for attr, value in attribute_updates.items():
            if attr in self.stats['attributes']:
                self.stats['attributes'][attr] += value
    
    def add_points(self, stat_category: str, stat_name: str, points: int = 1, update_related: bool = True):
        """
        Add points to a specific stat and update all related stats
        
        Args:
            stat_category: Category of stat (generation, leveling, monetization, engagement, game, attributes)
            stat_name: Name of the stat to update
            points: Number of points to add (default: 1)
            update_related: Whether to update related stats automatically (default: True)
        """
        if stat_category not in self.stats:
            print(f"[StatsCounter] Warning: Unknown stat category: {stat_category}")
            return False
        
        category_stats = self.stats[stat_category]
        
        # Update the specific stat
        if stat_name in category_stats:
            if isinstance(category_stats[stat_name], (int, float)):
                category_stats[stat_name] += points
            elif isinstance(category_stats[stat_name], dict):
                # For dict stats, increment a default key or create it
                if 'default' in category_stats[stat_name]:
                    category_stats[stat_name]['default'] += points
                else:
                    category_stats[stat_name]['total'] = category_stats[stat_name].get('total', 0) + points
            print(f"[StatsCounter] Added {points} points to {stat_category}.{stat_name} (new value: {category_stats[stat_name]})")
        else:
            # Create new stat if it doesn't exist
            category_stats[stat_name] = points
            print(f"[StatsCounter] Created new stat {stat_category}.{stat_name} with {points} points")
        
        # Update related stats if requested
        if update_related:
            self._update_related_stats(stat_category, stat_name, points)
        
        return True
    
    def _update_related_stats(self, stat_category: str, stat_name: str, points: int):
        """Update all stats related to the changed stat"""
        
        # Generation stats affect leveling and attributes
        if stat_category == 'generation':
            if stat_name in ['total_generations', 'successful_generations']:
                # Add XP for generations
                xp_gained = points * 10  # 10 XP per generation
                self.update_leveling_stats(xp_gained, 'generation')
                # Update attributes
                self.stats['attributes']['creativity'] = min(100, self.stats['attributes']['creativity'] + (points * 2))
                self.stats['attributes']['speed'] = min(100, self.stats['attributes']['speed'] + points)
            
            if stat_name == 'average_quality':
                # Quality affects quality_focus attribute
                quality_increase = points * 10
                self.stats['attributes']['quality_focus'] = min(100, self.stats['attributes']['quality_focus'] + quality_increase)
        
        # Leveling stats affect engagement and game stats
        elif stat_category == 'leveling':
            if stat_name == 'total_xp':
                # Level ups trigger achievements
                old_level = self.stats['leveling'].get('current_level', 1)
                from src.services.monetization.booster_pack_system import InfiniteLevelingSystem
                leveling_system = InfiniteLevelingSystem()
                new_level = leveling_system.calculate_level_from_xp(self.stats['leveling']['total_xp'])
                if new_level > old_level:
                    # Level up achievement
                    self.stats['game']['achievements_unlocked'] += 1
        
        # Engagement stats affect consistency attribute
        elif stat_category == 'engagement':
            if stat_name in ['days_active', 'streak_days']:
                consistency_increase = points * 5
                self.stats['attributes']['consistency'] = min(100, self.stats['attributes']['consistency'] + consistency_increase)
        
        # Game stats affect innovation and community attributes
        elif stat_category == 'game':
            if stat_name in ['quests_completed', 'achievements_unlocked']:
                innovation_increase = points * 2
                self.stats['attributes']['innovation'] = min(100, self.stats['attributes']['innovation'] + innovation_increase)
            
            if stat_name == 'trophies_earned':
                community_increase = points * 3
                self.stats['attributes']['community'] = min(100, self.stats['attributes']['community'] + community_increase)
        
        # Attributes affect overall stats
        elif stat_category == 'attributes':
            # Recalculate attributes from overall stats
            self.calculate_attributes_from_stats()
    
    def calculate_attributes_from_stats(self):
        """Calculate attributes based on overall stats"""
        gen_stats = self.stats['generation']
        level_stats = self.stats['leveling']
        game_stats = self.stats['game']
        
        # Creativity: based on variety of themes and generations
        creativity = min(100, (len(gen_stats['themes_used']) * 10) + (gen_stats['total_generations'] * 2))
        
        # Quality focus: based on average quality
        quality_focus = min(100, gen_stats['average_quality'] * 100)
        
        # Speed: based on generation frequency
        speed = min(100, (gen_stats['total_generations'] / max(1, self.stats['engagement']['days_active'])) * 10)
        
        # Consistency: based on streak and regular activity
        consistency = min(100, (self.stats['engagement']['streak_days'] * 5) + (self.stats['engagement']['days_active'] * 2))
        
        # Innovation: based on new features used
        innovation = min(100, (len(gen_stats['providers_used']) * 15) + (game_stats['achievements_unlocked'] * 2))
        
        # Community: based on sharing and social activity
        community = min(100, (game_stats['quests_completed'] * 3) + (game_stats['trophies_earned'] * 5))
        
        self.stats['attributes'] = {
            'creativity': creativity,
            'quality_focus': quality_focus,
            'speed': speed,
            'consistency': consistency,
            'innovation': innovation,
            'community': community
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get all statistics"""
        self.calculate_attributes_from_stats()
        return self.stats
    
    def get_stat_summary(self) -> Dict[str, Any]:
        """Get summary of all stats"""
        all_stats = self.get_all_stats()
        
        return {
            'total_generations': all_stats['generation']['total_generations'],
            'current_level': all_stats['leveling']['current_level'],
            'total_xp': all_stats['leveling']['total_xp'],
            'total_spent': all_stats['monetization']['total_spent'],
            'days_active': all_stats['engagement']['days_active'],
            'streak_days': all_stats['engagement']['streak_days'],
            'quests_completed': all_stats['game']['quests_completed'],
            'achievements_unlocked': all_stats['game']['achievements_unlocked'],
            'attributes': all_stats['attributes']
        }
    
    def get_stat(self, category: str, stat_name: str):
        """Get a specific stat value"""
        if category in self.stats and stat_name in self.stats[category]:
            return self.stats[category][stat_name]
        return None
    
    def increment_stat(self, category: str, stat_name: str, amount: int = 1):
        """Increment a stat by a specific amount (alias for add_points)"""
        return self.add_points(category, stat_name, amount, update_related=True)

