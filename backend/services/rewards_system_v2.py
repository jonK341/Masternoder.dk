"""
Rewards System v2.0 - Comprehensive Reward Management
- Database persistence
- Multiple reward types
- Daily/weekly/monthly rewards
- Achievement rewards
- Battle rewards
- Video generation rewards
- Social rewards
- Streak rewards
- Level-up rewards
- Quest/mission rewards
- Special event rewards
- Reward tiers and rarities
"""
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    unified_points_db = UnifiedPointsDatabase()
except ImportError:
    unified_points_db = None

try:
    from backend.services.point_connection_system import PointConnectionSystem
    point_connection = PointConnectionSystem()
except ImportError:
    point_connection = None


class RewardsSystemV2:
    """Comprehensive rewards system with database persistence"""
    
    def __init__(self):
        self.reward_categories = {
            'daily': {'name': 'Daily Rewards', 'icon': '📅', 'color': '#00ff88'},
            'weekly': {'name': 'Weekly Rewards', 'icon': '📆', 'color': '#00d4ff'},
            'monthly': {'name': 'Monthly Rewards', 'icon': '🗓️', 'color': '#ff00ff'},
            'achievement': {'name': 'Achievement Rewards', 'icon': '🏆', 'color': '#ffaa00'},
            'battle': {'name': 'Battle Rewards', 'icon': '⚔️', 'color': '#ff4444'},
            'generation': {'name': 'Video Generation Rewards', 'icon': '🎬', 'color': '#00ffff'},
            'social': {'name': 'Social Rewards', 'icon': '👥', 'color': '#44ff44'},
            'streak': {'name': 'Streak Rewards', 'icon': '🔥', 'color': '#ff8800'},
            'level_up': {'name': 'Level Up Rewards', 'icon': '⬆️', 'color': '#8888ff'},
            'quest': {'name': 'Quest Rewards', 'icon': '📋', 'color': '#ff8888'},
            'mission': {'name': 'Mission Rewards', 'icon': '🎯', 'color': '#aa88ff'},
            'event': {'name': 'Special Event Rewards', 'icon': '🎉', 'color': '#ffff00'},
            'shop': {'name': 'Shop Rewards', 'icon': '🛒', 'color': '#88ff88'},
            'champions_league': {'name': 'Champions League Rewards', 'icon': '👑', 'color': '#ffd700'},
            'activity': {'name': 'Activity Rewards', 'icon': '📊', 'color': '#00ff00'},
            'discovery': {'name': 'Discovery Rewards', 'icon': '🔍', 'color': '#ff00ff'},
            'milestone': {'name': 'Milestone Rewards', 'icon': '🎯', 'color': '#ff8800'},
            'referral': {'name': 'Referral Rewards', 'icon': '🔗', 'color': '#00d4ff'},
            'quality': {'name': 'Quality Rewards', 'icon': '✨', 'color': '#ffd700'},
            'speed': {'name': 'Speed Rewards', 'icon': '⚡', 'color': '#ff4444'},
            'collection': {'name': 'Collection Rewards', 'icon': '📦', 'color': '#aa00ff'},
            'exploration': {'name': 'Exploration Rewards', 'icon': '🗺️', 'color': '#00ffff'},
            'collaboration': {'name': 'Collaboration Rewards', 'icon': '🤝', 'color': '#44ff44'},
            'innovation': {'name': 'Innovation Rewards', 'icon': '💡', 'color': '#ffff00'},
            'mastery': {'name': 'Mastery Rewards', 'icon': '🎓', 'color': '#ffaa00'},
            'seasonal': {'name': 'Seasonal Rewards', 'icon': '🌸', 'color': '#ff88ff'},
            'anniversary': {'name': 'Anniversary Rewards', 'icon': '🎂', 'color': '#ffd700'},
            'birthday': {'name': 'Birthday Rewards', 'icon': '🎈', 'color': '#ff00ff'},
            'first_time': {'name': 'First Time Rewards', 'icon': '🌟', 'color': '#00ff88'},
            'combo': {'name': 'Combo Rewards', 'icon': '💥', 'color': '#ff4444'},
            'lucky': {'name': 'Lucky Rewards', 'icon': '🍀', 'color': '#00ff00'},
            'bundle': {'name': 'Reward Bundles', 'icon': '📦', 'color': '#ff8800'},
        }
        
        self.reward_types = {
            'points': {'name': 'Points', 'icon': '⭐', 'apply': self._apply_points_reward},
            'xp': {'name': 'XP', 'icon': '💫', 'apply': self._apply_xp_reward},
            'coins': {'name': 'Coins', 'icon': '🪙', 'apply': self._apply_coins_reward},
            'credits': {'name': 'Credits', 'icon': '💎', 'apply': self._apply_credits_reward},
            'stat_points': {'name': 'Stat Points', 'icon': '📊', 'apply': self._apply_stat_points_reward},
            'trophy': {'name': 'Trophy', 'icon': '🏆', 'apply': self._apply_trophy_reward},
            'item': {'name': 'Item', 'icon': '📦', 'apply': self._apply_item_reward},
            'artifact': {'name': 'Artifact', 'icon': '🔮', 'apply': self._apply_artifact_reward},
            'booster': {'name': 'Booster', 'icon': '⚡', 'apply': self._apply_booster_reward},
            'theme_unlock': {'name': 'Theme Unlock', 'icon': '🎨', 'apply': self._apply_theme_unlock_reward},
            'title': {'name': 'Title', 'icon': '👑', 'apply': self._apply_title_reward},
            'badge': {'name': 'Badge', 'icon': '🎖️', 'apply': self._apply_badge_reward},
            'multiplier': {'name': 'Multiplier', 'icon': '📈', 'apply': self._apply_multiplier_reward},
            'energy': {'name': 'Energy', 'icon': '⚡', 'apply': self._apply_energy_reward},
            'gems': {'name': 'Gems', 'icon': '💠', 'apply': self._apply_gems_reward},
            'tokens': {'name': 'Tokens', 'icon': '🪙', 'apply': self._apply_tokens_reward},
            'crystals': {'name': 'Crystals', 'icon': '💎', 'apply': self._apply_crystals_reward},
            'prestige': {'name': 'Prestige Points', 'icon': '⭐', 'apply': self._apply_prestige_reward},
            'mastery': {'name': 'Mastery Points', 'icon': '🎓', 'apply': self._apply_mastery_reward},
            'reputation': {'name': 'Reputation', 'icon': '⭐', 'apply': self._apply_reputation_reward},
            'fame': {'name': 'Fame', 'icon': '🌟', 'apply': self._apply_fame_reward},
            'honor': {'name': 'Honor', 'icon': '⚔️', 'apply': self._apply_honor_reward},
            'wisdom': {'name': 'Wisdom', 'icon': '📚', 'apply': self._apply_wisdom_reward},
            'luck': {'name': 'Luck', 'icon': '🍀', 'apply': self._apply_luck_reward},
            'fortune': {'name': 'Fortune', 'icon': '💰', 'apply': self._apply_fortune_reward},
            'power': {'name': 'Power', 'icon': '⚡', 'apply': self._apply_power_reward},
            'skill': {'name': 'Skill Points', 'icon': '🎯', 'apply': self._apply_skill_reward},
            'experience': {'name': 'Experience', 'icon': '💫', 'apply': self._apply_experience_reward},
            'knowledge': {'name': 'Knowledge', 'icon': '🧠', 'apply': self._apply_knowledge_reward},
            'inspiration': {'name': 'Inspiration', 'icon': '💡', 'apply': self._apply_inspiration_reward},
            'creativity': {'name': 'Creativity', 'icon': '🎨', 'apply': self._apply_creativity_reward},
            'stamina': {'name': 'Stamina', 'icon': '💪', 'apply': self._apply_stamina_reward},
            'health': {'name': 'Health', 'icon': '❤️', 'apply': self._apply_health_reward},
            'mana': {'name': 'Mana', 'icon': '🔮', 'apply': self._apply_mana_reward},
            'shield': {'name': 'Shield', 'icon': '🛡️', 'apply': self._apply_shield_reward},
            'weapon': {'name': 'Weapon', 'icon': '⚔️', 'apply': self._apply_weapon_reward},
            'armor': {'name': 'Armor', 'icon': '🛡️', 'apply': self._apply_armor_reward},
            'accessory': {'name': 'Accessory', 'icon': '💍', 'apply': self._apply_accessory_reward},
            'consumable': {'name': 'Consumable', 'icon': '🧪', 'apply': self._apply_consumable_reward},
            'recipe': {'name': 'Recipe', 'icon': '📜', 'apply': self._apply_recipe_reward},
            'blueprint': {'name': 'Blueprint', 'icon': '📐', 'apply': self._apply_blueprint_reward},
            'key': {'name': 'Key', 'icon': '🗝️', 'apply': self._apply_key_reward},
            'scroll': {'name': 'Scroll', 'icon': '📜', 'apply': self._apply_scroll_reward},
            'potion': {'name': 'Potion', 'icon': '🧪', 'apply': self._apply_potion_reward},
            'elixir': {'name': 'Elixir', 'icon': '⚗️', 'apply': self._apply_elixir_reward},
            'bundle': {'name': 'Reward Bundle', 'icon': '📦', 'apply': self._apply_bundle_reward},
        }
        
        self.reward_rarities = {
            'common': {'name': 'Common', 'color': '#888888', 'multiplier': 1.0},
            'uncommon': {'name': 'Uncommon', 'color': '#00ff00', 'multiplier': 1.5},
            'rare': {'name': 'Rare', 'color': '#0088ff', 'multiplier': 2.0},
            'epic': {'name': 'Epic', 'color': '#aa00ff', 'multiplier': 3.0},
            'legendary': {'name': 'Legendary', 'color': '#ffaa00', 'multiplier': 5.0},
            'mythic': {'name': 'Mythic', 'color': '#ff0088', 'multiplier': 10.0},
        }
    
    def _award_leaderboard_points(self, user_id: str, reward_data: Dict, base_points: int = 0) -> int:
        """
        Award points to leaderboard systems for any reward type
        Ensures all rewards contribute to leaderboard rankings
        
        Args:
            user_id: User identifier
            reward_data: Reward data dictionary
            base_points: Base points to award (if not in reward_data)
            
        Returns:
            Total points awarded
        """
        if not point_connection:
            return 0
        
        # Get points from reward data or use base_points
        points = reward_data.get('amount', base_points)
        if points <= 0:
            points = reward_data.get('points', 0)
        if points <= 0:
            points = base_points
        
        # Get rarity multiplier
        rarity = reward_data.get('rarity', 'common')
        rarity_multiplier = self.reward_rarities.get(rarity, {}).get('multiplier', 1.0)
        total_points = int(points * rarity_multiplier)
        
        # Award to reward_points system (primary)
        point_connection.ensure_point_counting(user_id, 'reward_points', total_points, 'reward_system')
        
        # Award to activity_points for leaderboard visibility (10% bonus)
        activity_bonus = int(total_points * 0.1)
        if activity_bonus > 0:
            point_connection.ensure_point_counting(user_id, 'activity_points', activity_bonus, 'reward_system')
        
        return total_points
    
    def _apply_points_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply points reward - awards to multiple point systems"""
        amount = reward_data.get('amount', 0)
        bonus_points = reward_data.get('bonus_points', 0)
        total_points = amount + bonus_points
        
        # Award to reward_points system
        if point_connection:
            point_connection.ensure_point_counting(user_id, 'reward_points', amount, 'reward_system')
            # Also award to activity_points for leaderboard visibility
            point_connection.ensure_point_counting(user_id, 'activity_points', int(amount * 0.1), 'reward_system')
        
        return {
            'success': True, 
            'points_awarded': amount,
            'bonus_points': bonus_points,
            'total_points': total_points
        }
    
    def _apply_xp_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply XP reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if point_connection:
            point_connection.ensure_point_counting(user_id, 'xp', amount, 'reward_system')
            # Award points equivalent to XP for leaderboard
            point_connection.ensure_point_counting(user_id, 'xp_points', amount, 'reward_system')
            # Also award to reward_points
            point_connection.ensure_point_counting(user_id, 'reward_points', int(amount * 0.5), 'reward_system')
        return {'success': True, 'xp_awarded': amount, 'points_awarded': amount}
    
    def _apply_coins_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply coins reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'coins', amount)
        # Award points equivalent to coins for leaderboard
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'coins_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_credits_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply credits reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'credits', amount)
        # Award points equivalent to credits for leaderboard
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'credits_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_stat_points_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply stat points reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'stats_points', amount)
        # Award points equivalent to stat points for leaderboard
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        if point_connection:
            point_connection.ensure_point_counting(user_id, 'stats_points', amount, 'reward_system')
        return {'success': True, 'stat_points_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_trophy_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply trophy reward - also awards points to leaderboard"""
        trophy_id = reward_data.get('trophy_id', '')
        trophy_points = reward_data.get('points', 100)  # Default 100 points per trophy
        
        if unified_points_db:
            # Store trophy in user profile
            profile = unified_points_db.get_user_profile(user_id)
            if 'trophies' not in profile.get('preferences', {}):
                profile['preferences']['trophies'] = []
            if trophy_id not in profile['preferences']['trophies']:
                profile['preferences']['trophies'].append(trophy_id)
                unified_points_db.save_user_profile(user_id, profile)
        
        # Award points for trophy (trophies are valuable!)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, trophy_points)
        if point_connection:
            point_connection.ensure_point_counting(user_id, 'trophy_points', trophy_points, 'reward_system')
        
        return {'success': True, 'trophy_awarded': trophy_id, 'points_awarded': points_awarded}
    
    def _apply_item_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply item reward - also awards points to leaderboard"""
        item_id = reward_data.get('item_id', '')
        quantity = reward_data.get('quantity', 1)
        item_value = reward_data.get('value', 50)  # Default 50 points per item
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'inventory' not in profile.get('preferences', {}):
                profile['preferences']['inventory'] = {}
            if item_id in profile['preferences']['inventory']:
                profile['preferences']['inventory'][item_id] += quantity
            else:
                profile['preferences']['inventory'][item_id] = quantity
            unified_points_db.save_user_profile(user_id, profile)
        
        # Award points based on item value and quantity
        points_awarded = self._award_leaderboard_points(user_id, reward_data, item_value * quantity)
        
        return {'success': True, 'item_awarded': item_id, 'quantity': quantity, 'points_awarded': points_awarded}
    
    def _apply_artifact_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply artifact reward - also awards points to leaderboard"""
        artifact_id = reward_data.get('artifact_id', '')
        artifact_value = reward_data.get('value', 500)  # Artifacts are valuable!
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'artifacts' not in profile.get('preferences', {}):
                profile['preferences']['artifacts'] = []
            if artifact_id not in profile['preferences']['artifacts']:
                profile['preferences']['artifacts'].append(artifact_id)
                unified_points_db.save_user_profile(user_id, profile)
        
        # Award significant points for artifacts
        points_awarded = self._award_leaderboard_points(user_id, reward_data, artifact_value)
        
        return {'success': True, 'artifact_awarded': artifact_id, 'points_awarded': points_awarded}
    
    def _apply_booster_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply booster reward - also awards points to leaderboard"""
        booster_id = reward_data.get('booster_id', '')
        duration = reward_data.get('duration', 3600)
        booster_value = reward_data.get('value', 75)  # Default 75 points per booster
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'active_boosters' not in profile.get('preferences', {}):
                profile['preferences']['active_boosters'] = {}
            profile['preferences']['active_boosters'][booster_id] = {
                'activated_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(seconds=duration)).isoformat(),
                'effects': reward_data.get('effects', {})
            }
            unified_points_db.save_user_profile(user_id, profile)
        
        # Award points for booster
        points_awarded = self._award_leaderboard_points(user_id, reward_data, booster_value)
        
        return {'success': True, 'booster_awarded': booster_id, 'points_awarded': points_awarded}
    
    def _apply_theme_unlock_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply theme unlock reward - also awards points to leaderboard"""
        theme_id = reward_data.get('theme_id', '')
        theme_value = reward_data.get('value', 200)  # Theme unlocks are valuable
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'unlocked_themes' not in profile.get('preferences', {}):
                profile['preferences']['unlocked_themes'] = []
            if theme_id not in profile['preferences']['unlocked_themes']:
                profile['preferences']['unlocked_themes'].append(theme_id)
                unified_points_db.save_user_profile(user_id, profile)
        
        # Award points for theme unlock
        points_awarded = self._award_leaderboard_points(user_id, reward_data, theme_value)
        if point_connection:
            point_connection.ensure_point_counting(user_id, 'theme_points', theme_value, 'reward_system')
        
        return {'success': True, 'theme_unlocked': theme_id, 'points_awarded': points_awarded}
    
    def _apply_title_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply title reward - also awards points to leaderboard"""
        title_id = reward_data.get('title_id', '')
        title_value = reward_data.get('value', 150)  # Titles are prestigious
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'unlocked_titles' not in profile.get('preferences', {}):
                profile['preferences']['unlocked_titles'] = []
            if title_id not in profile['preferences']['unlocked_titles']:
                profile['preferences']['unlocked_titles'].append(title_id)
                unified_points_db.save_user_profile(user_id, profile)
        
        # Award points for title
        points_awarded = self._award_leaderboard_points(user_id, reward_data, title_value)
        
        return {'success': True, 'title_unlocked': title_id, 'points_awarded': points_awarded}
    
    def _apply_badge_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply badge reward - also awards points to leaderboard"""
        badge_id = reward_data.get('badge_id', '')
        badge_value = reward_data.get('value', 50)  # Default 50 points per badge
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'badges' not in profile.get('preferences', {}):
                profile['preferences']['badges'] = []
            if badge_id not in profile['preferences']['badges']:
                profile['preferences']['badges'].append(badge_id)
                unified_points_db.save_user_profile(user_id, profile)
        
        # Award points for badge
        points_awarded = self._award_leaderboard_points(user_id, reward_data, badge_value)
        
        return {'success': True, 'badge_awarded': badge_id, 'points_awarded': points_awarded}
    
    def _apply_multiplier_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply multiplier reward - also awards points to leaderboard"""
        multiplier_type = reward_data.get('multiplier_type', 'xp')
        multiplier_value = reward_data.get('multiplier_value', 1.5)
        duration = reward_data.get('duration', 3600)
        multiplier_points = reward_data.get('value', 100)  # Multipliers are valuable
        
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'active_multipliers' not in profile.get('preferences', {}):
                profile['preferences']['active_multipliers'] = {}
            profile['preferences']['active_multipliers'][multiplier_type] = {
                'value': multiplier_value,
                'activated_at': datetime.utcnow().isoformat(),
                'expires_at': (datetime.utcnow() + timedelta(seconds=duration)).isoformat()
            }
            unified_points_db.save_user_profile(user_id, profile)
        
        # Award points for multiplier
        points_awarded = self._award_leaderboard_points(user_id, reward_data, multiplier_points)
        
        return {'success': True, 'multiplier_awarded': multiplier_type, 'value': multiplier_value, 'points_awarded': points_awarded}
    
    def _apply_energy_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply energy reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'energy', amount)
        # Award points equivalent to energy for leaderboard
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'energy_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_gems_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply gems reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'gems', amount)
        # Award points equivalent to gems for leaderboard (gems are valuable!)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount * 2)  # Gems worth 2x points
        return {'success': True, 'gems_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_tokens_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply tokens reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'tokens', amount)
        # Award points equivalent to tokens for leaderboard
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'tokens_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_crystals_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply crystals reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'crystals', amount)
        # Award points equivalent to crystals for leaderboard (crystals are valuable!)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount * 3)  # Crystals worth 3x points
        return {'success': True, 'crystals_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_prestige_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply prestige reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'prestige', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount * 2)
        return {'success': True, 'prestige_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_mastery_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply mastery reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'mastery', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount * 1.5)
        return {'success': True, 'mastery_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_reputation_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply reputation reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'reputation', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'reputation_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_fame_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply fame reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'fame', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'fame_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_honor_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply honor reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'honor', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'honor_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_wisdom_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply wisdom reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'wisdom', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'wisdom_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_luck_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply luck reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'luck', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'luck_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_fortune_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply fortune reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'fortune', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'fortune_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_power_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply power reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'power', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'power_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_skill_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply skill reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'skill', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'skill_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_experience_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply experience reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'experience', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'experience_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_knowledge_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply knowledge reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'knowledge', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'knowledge_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_inspiration_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply inspiration reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'inspiration', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'inspiration_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_creativity_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply creativity reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'creativity', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'creativity_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_stamina_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply stamina reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'stamina', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'stamina_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_health_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply health reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'health', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'health_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_mana_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply mana reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'mana', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'mana_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_shield_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply shield reward - also awards points to leaderboard"""
        amount = reward_data.get('amount', 0)
        if unified_points_db:
            unified_points_db.add_points(user_id, 'shield', amount)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, amount)
        return {'success': True, 'shield_awarded': amount, 'points_awarded': points_awarded}
    
    def _apply_weapon_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply weapon reward - also awards points to leaderboard"""
        weapon_id = reward_data.get('weapon_id', '')
        weapon_value = reward_data.get('value', 300)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'weapons' not in profile.get('preferences', {}):
                profile['preferences']['weapons'] = []
            if weapon_id not in profile['preferences']['weapons']:
                profile['preferences']['weapons'].append(weapon_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, weapon_value)
        return {'success': True, 'weapon_awarded': weapon_id, 'points_awarded': points_awarded}
    
    def _apply_armor_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply armor reward - also awards points to leaderboard"""
        armor_id = reward_data.get('armor_id', '')
        armor_value = reward_data.get('value', 250)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'armor' not in profile.get('preferences', {}):
                profile['preferences']['armor'] = []
            if armor_id not in profile['preferences']['armor']:
                profile['preferences']['armor'].append(armor_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, armor_value)
        return {'success': True, 'armor_awarded': armor_id, 'points_awarded': points_awarded}
    
    def _apply_accessory_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply accessory reward - also awards points to leaderboard"""
        accessory_id = reward_data.get('accessory_id', '')
        accessory_value = reward_data.get('value', 150)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'accessories' not in profile.get('preferences', {}):
                profile['preferences']['accessories'] = []
            if accessory_id not in profile['preferences']['accessories']:
                profile['preferences']['accessories'].append(accessory_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, accessory_value)
        return {'success': True, 'accessory_awarded': accessory_id, 'points_awarded': points_awarded}
    
    def _apply_consumable_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply consumable reward - also awards points to leaderboard"""
        consumable_id = reward_data.get('consumable_id', '')
        quantity = reward_data.get('quantity', 1)
        consumable_value = reward_data.get('value', 25)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'consumables' not in profile.get('preferences', {}):
                profile['preferences']['consumables'] = {}
            if consumable_id in profile['preferences']['consumables']:
                profile['preferences']['consumables'][consumable_id] += quantity
            else:
                profile['preferences']['consumables'][consumable_id] = quantity
            unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, consumable_value * quantity)
        return {'success': True, 'consumable_awarded': consumable_id, 'quantity': quantity, 'points_awarded': points_awarded}
    
    def _apply_recipe_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply recipe reward - also awards points to leaderboard"""
        recipe_id = reward_data.get('recipe_id', '')
        recipe_value = reward_data.get('value', 200)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'recipes' not in profile.get('preferences', {}):
                profile['preferences']['recipes'] = []
            if recipe_id not in profile['preferences']['recipes']:
                profile['preferences']['recipes'].append(recipe_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, recipe_value)
        return {'success': True, 'recipe_awarded': recipe_id, 'points_awarded': points_awarded}
    
    def _apply_blueprint_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply blueprint reward - also awards points to leaderboard"""
        blueprint_id = reward_data.get('blueprint_id', '')
        blueprint_value = reward_data.get('value', 300)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'blueprints' not in profile.get('preferences', {}):
                profile['preferences']['blueprints'] = []
            if blueprint_id not in profile['preferences']['blueprints']:
                profile['preferences']['blueprints'].append(blueprint_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, blueprint_value)
        return {'success': True, 'blueprint_awarded': blueprint_id, 'points_awarded': points_awarded}
    
    def _apply_key_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply key reward - also awards points to leaderboard"""
        key_id = reward_data.get('key_id', '')
        key_value = reward_data.get('value', 100)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'keys' not in profile.get('preferences', {}):
                profile['preferences']['keys'] = []
            if key_id not in profile['preferences']['keys']:
                profile['preferences']['keys'].append(key_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, key_value)
        return {'success': True, 'key_awarded': key_id, 'points_awarded': points_awarded}
    
    def _apply_scroll_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply scroll reward - also awards points to leaderboard"""
        scroll_id = reward_data.get('scroll_id', '')
        scroll_value = reward_data.get('value', 150)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'scrolls' not in profile.get('preferences', {}):
                profile['preferences']['scrolls'] = []
            if scroll_id not in profile['preferences']['scrolls']:
                profile['preferences']['scrolls'].append(scroll_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, scroll_value)
        return {'success': True, 'scroll_awarded': scroll_id, 'points_awarded': points_awarded}
    
    def _apply_potion_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply potion reward - also awards points to leaderboard"""
        potion_id = reward_data.get('potion_id', '')
        quantity = reward_data.get('quantity', 1)
        potion_value = reward_data.get('value', 50)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'potions' not in profile.get('preferences', {}):
                profile['preferences']['potions'] = {}
            if potion_id in profile['preferences']['potions']:
                profile['preferences']['potions'][potion_id] += quantity
            else:
                profile['preferences']['potions'][potion_id] = quantity
            unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, potion_value * quantity)
        return {'success': True, 'potion_awarded': potion_id, 'quantity': quantity, 'points_awarded': points_awarded}
    
    def _apply_elixir_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply elixir reward - also awards points to leaderboard"""
        elixir_id = reward_data.get('elixir_id', '')
        quantity = reward_data.get('quantity', 1)
        elixir_value = reward_data.get('value', 75)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'elixirs' not in profile.get('preferences', {}):
                profile['preferences']['elixirs'] = {}
            if elixir_id in profile['preferences']['elixirs']:
                profile['preferences']['elixirs'][elixir_id] += quantity
            else:
                profile['preferences']['elixirs'][elixir_id] = quantity
            unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, elixir_value * quantity)
        return {'success': True, 'elixir_awarded': elixir_id, 'quantity': quantity, 'points_awarded': points_awarded}
    
    def _apply_bundle_reward(self, user_id: str, reward_data: Dict) -> Dict[str, Any]:
        """Apply bundle reward - also awards points to leaderboard"""
        bundle_id = reward_data.get('bundle_id', '')
        bundle_items = reward_data.get('items', [])
        bundle_value = reward_data.get('value', 500)
        if unified_points_db:
            profile = unified_points_db.get_user_profile(user_id)
            if 'bundles' not in profile.get('preferences', {}):
                profile['preferences']['bundles'] = []
            if bundle_id not in profile['preferences']['bundles']:
                profile['preferences']['bundles'].append(bundle_id)
                unified_points_db.save_user_profile(user_id, profile)
        points_awarded = self._award_leaderboard_points(user_id, reward_data, bundle_value)
        return {'success': True, 'bundle_awarded': bundle_id, 'items': bundle_items, 'points_awarded': points_awarded}
    
    def create_reward(
        self,
        user_id: str,
        category: str,
        reward_type: str,
        amount: Optional[int] = None,
        rarity: str = 'common',
        description: str = "",
        source: str = "",
        metadata: Optional[Dict] = None,
        expires_at: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Create a new reward"""
        if category not in self.reward_categories:
            return {'success': False, 'error': f'Invalid category: {category}'}
        
        if reward_type not in self.reward_types:
            return {'success': False, 'error': f'Invalid reward type: {reward_type}'}
        
        if rarity not in self.reward_rarities:
            rarity = 'common'
        
        reward_id = str(uuid.uuid4())
        reward = {
            'reward_id': reward_id,
            'user_id': user_id,
            'category': category,
            'reward_type': reward_type,
            'amount': amount,
            'rarity': rarity,
            'description': description,
            'source': source,
            'metadata': metadata or {},
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': expires_at.isoformat() if expires_at else None
        }
        
        # Save to database
        if unified_points_db:
            try:
                profile = unified_points_db.get_user_profile(user_id)
                if not profile:
                    profile = {'preferences': {}}
                if 'preferences' not in profile:
                    profile['preferences'] = {}
                if 'pending_rewards' not in profile['preferences']:
                    profile['preferences']['pending_rewards'] = []
                profile['preferences']['pending_rewards'].append(reward)
                unified_points_db.save_user_profile(user_id, profile)
            except Exception as e:
                print(f"[RewardsSystemV2] Error saving reward: {e}")
        
        return {
            'success': True,
            'reward': reward
        }
    
    def claim_reward(self, user_id: str, reward_id: str) -> Dict[str, Any]:
        """Claim a pending reward"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        profile = unified_points_db.get_user_profile(user_id)
        pending_rewards = profile.get('preferences', {}).get('pending_rewards', [])
        
        reward = None
        for r in pending_rewards:
            if r.get('reward_id') == reward_id:
                reward = r
                break
        
        if not reward:
            return {'success': False, 'error': 'Reward not found'}
        
        if reward.get('status') != 'pending':
            return {'success': False, 'error': 'Reward already claimed'}
        
        # Check expiration
        if reward.get('expires_at'):
            expires_at = datetime.fromisoformat(reward['expires_at'])
            if datetime.utcnow() > expires_at:
                return {'success': False, 'error': 'Reward expired'}
        
        # Apply reward
        reward_type = reward.get('reward_type')
        if reward_type in self.reward_types:
            apply_func = self.reward_types[reward_type]['apply']
            apply_result = apply_func(user_id, reward)
        else:
            apply_result = {'success': False, 'error': 'Unknown reward type'}
        
        if not apply_result.get('success'):
            return apply_result
        
        # Update reward status
        reward['status'] = 'claimed'
        reward['claimed_at'] = datetime.utcnow().isoformat()
        reward['apply_result'] = apply_result
        
        # Move to history
        if 'reward_history' not in profile.get('preferences', {}):
            profile['preferences']['reward_history'] = []
        profile['preferences']['reward_history'].append(reward)
        
        # Remove from pending
        profile['preferences']['pending_rewards'] = [
            r for r in pending_rewards if r.get('reward_id') != reward_id
        ]
        
        unified_points_db.save_user_profile(user_id, profile)
        
        return {
            'success': True,
            'reward': reward,
            'apply_result': apply_result
        }
    
    def claim_all_rewards(self, user_id: str) -> Dict[str, Any]:
        """Claim all pending rewards"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        profile = unified_points_db.get_user_profile(user_id)
        pending_rewards = profile.get('preferences', {}).get('pending_rewards', [])
        
        claimed = []
        failed = []
        
        for reward in pending_rewards[:]:
            result = self.claim_reward(user_id, reward.get('reward_id'))
            if result.get('success'):
                claimed.append(reward)
            else:
                failed.append({'reward_id': reward.get('reward_id'), 'error': result.get('error')})
        
        return {
            'success': True,
            'claimed_count': len(claimed),
            'failed_count': len(failed),
            'claimed_rewards': claimed,
            'failed_rewards': failed
        }
    
    def get_user_rewards(self, user_id: str, include_history: bool = True) -> Dict[str, Any]:
        """Get user's rewards"""
        if not unified_points_db:
            return {
                'success': True,
                'pending_rewards': [],
                'reward_history': [],
                'statistics': {}
            }
        
        profile = unified_points_db.get_user_profile(user_id)
        preferences = profile.get('preferences', {})
        
        pending_rewards = preferences.get('pending_rewards', [])
        reward_history = preferences.get('reward_history', [])[-100:] if include_history else []
        
        # Filter expired rewards
        now = datetime.utcnow()
        valid_pending = []
        expired = []
        
        for reward in pending_rewards:
            if reward.get('expires_at'):
                expires_at = datetime.fromisoformat(reward['expires_at'])
                if now > expires_at:
                    expired.append(reward)
                    continue
            valid_pending.append(reward)
        
        # Remove expired from pending
        if expired:
            profile['preferences']['pending_rewards'] = valid_pending
            unified_points_db.save_user_profile(user_id, profile)
        
        # Calculate statistics
        stats = self._calculate_reward_statistics(user_id, reward_history)
        
        return {
            'success': True,
            'pending_rewards': valid_pending,
            'reward_history': reward_history,
            'expired_rewards': expired,
            'statistics': stats
        }
    
    def _calculate_reward_statistics(self, user_id: str, reward_history: List[Dict]) -> Dict[str, Any]:
        """Calculate reward statistics"""
        stats = {
            'total_claimed': len(reward_history),
            'by_category': defaultdict(int),
            'by_type': defaultdict(int),
            'by_rarity': defaultdict(int),
            'total_points': 0,
            'total_xp': 0,
            'total_coins': 0,
            'total_credits': 0,
        }
        
        for reward in reward_history:
            category = reward.get('category', 'unknown')
            reward_type = reward.get('reward_type', 'unknown')
            rarity = reward.get('rarity', 'common')
            
            stats['by_category'][category] += 1
            stats['by_type'][reward_type] += 1
            stats['by_rarity'][rarity] += 1
            
            amount = reward.get('amount', 0)
            if reward_type == 'points':
                stats['total_points'] += amount
            elif reward_type == 'xp':
                stats['total_xp'] += amount
            elif reward_type == 'coins':
                stats['total_coins'] += amount
            elif reward_type == 'credits':
                stats['total_credits'] += amount
        
        stats['by_category'] = dict(stats['by_category'])
        stats['by_type'] = dict(stats['by_type'])
        stats['by_rarity'] = dict(stats['by_rarity'])
        
        return stats
    
    # Daily/Weekly/Monthly Rewards
    def get_daily_reward(self, user_id: str) -> Dict[str, Any]:
        """Get daily reward for user"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        profile = unified_points_db.get_user_profile(user_id)
        preferences = profile.get('preferences', {})
        
        last_daily = preferences.get('last_daily_reward')
        today = datetime.utcnow().date()
        
        if last_daily:
            last_date = datetime.fromisoformat(last_daily).date()
            if last_date == today:
                return {'success': False, 'error': 'Daily reward already claimed today'}
        
        # Calculate streak
        streak = preferences.get('daily_streak', 0)
        if last_daily:
            last_date = datetime.fromisoformat(last_daily).date()
            yesterday = today - timedelta(days=1)
            if last_date == yesterday:
                streak += 1
            else:
                streak = 1
        else:
            streak = 1
        
        # Calculate reward based on streak
        base_reward = 50
        streak_bonus = min(streak * 10, 200)  # Max 200 bonus
        total_reward = base_reward + streak_bonus
        
        # Create reward
        reward = self.create_reward(
            user_id=user_id,
            category='daily',
            reward_type='points',
            amount=total_reward,
            rarity='common' if streak < 7 else 'rare' if streak < 30 else 'epic',
            description=f'Daily login reward (Streak: {streak} days)',
            source='daily_login',
            metadata={'streak': streak, 'base_reward': base_reward, 'streak_bonus': streak_bonus}
        )
        
        # Update last daily reward
        preferences['last_daily_reward'] = datetime.utcnow().isoformat()
        preferences['daily_streak'] = streak
        profile['preferences'] = preferences
        unified_points_db.save_user_profile(user_id, profile)
        
        return reward
    
    def get_weekly_reward(self, user_id: str) -> Dict[str, Any]:
        """Get weekly reward for user"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        profile = unified_points_db.get_user_profile(user_id)
        preferences = profile.get('preferences', {})
        
        last_weekly = preferences.get('last_weekly_reward')
        now = datetime.utcnow()
        week_start = now - timedelta(days=now.weekday())
        
        if last_weekly:
            last_date = datetime.fromisoformat(last_weekly)
            last_week_start = last_date - timedelta(days=last_date.weekday())
            if last_week_start == week_start:
                return {'success': False, 'error': 'Weekly reward already claimed this week'}
        
        # Weekly reward
        reward = self.create_reward(
            user_id=user_id,
            category='weekly',
            reward_type='points',
            amount=500,
            rarity='rare',
            description='Weekly login reward',
            source='weekly_login'
        )
        
        # Also award bonus items
        self.create_reward(
            user_id=user_id,
            category='weekly',
            reward_type='stat_points',
            amount=5,
            rarity='uncommon',
            description='Weekly stat points bonus',
            source='weekly_login'
        )
        
        # Update last weekly reward
        preferences['last_weekly_reward'] = datetime.utcnow().isoformat()
        profile['preferences'] = preferences
        unified_points_db.save_user_profile(user_id, profile)
        
        return reward
    
    def get_monthly_reward(self, user_id: str) -> Dict[str, Any]:
        """Get monthly reward for user"""
        if not unified_points_db:
            return {'success': False, 'error': 'Database not available'}
        
        profile = unified_points_db.get_user_profile(user_id)
        preferences = profile.get('preferences', {})
        
        last_monthly = preferences.get('last_monthly_reward')
        now = datetime.utcnow()
        month_start = now.replace(day=1)
        
        if last_monthly:
            last_date = datetime.fromisoformat(last_monthly)
            last_month_start = last_date.replace(day=1)
            if last_month_start == month_start:
                return {'success': False, 'error': 'Monthly reward already claimed this month'}
        
        # Monthly reward
        reward = self.create_reward(
            user_id=user_id,
            category='monthly',
            reward_type='points',
            amount=2000,
            rarity='epic',
            description='Monthly login reward',
            source='monthly_login'
        )
        
        # Also award bonus items
        self.create_reward(
            user_id=user_id,
            category='monthly',
            reward_type='stat_points',
            amount=20,
            rarity='rare',
            description='Monthly stat points bonus',
            source='monthly_login'
        )
        
        self.create_reward(
            user_id=user_id,
            category='monthly',
            reward_type='coins',
            amount=500,
            rarity='rare',
            description='Monthly coins bonus',
            source='monthly_login'
        )
        
        # Update last monthly reward
        preferences['last_monthly_reward'] = datetime.utcnow().isoformat()
        profile['preferences'] = preferences
        unified_points_db.save_user_profile(user_id, profile)
        
        return reward
    
    # Battle Rewards
    def add_battle_reward(self, user_id: str, battle_result: Dict) -> Dict[str, Any]:
        """Add reward from battle"""
        won = battle_result.get('won', False)
        battle_type = battle_result.get('battle_type', 'quick')
        
        if won:
            points = 100 if battle_type == 'quick' else 200
            rarity = 'uncommon' if battle_type == 'quick' else 'rare'
            
            reward = self.create_reward(
                user_id=user_id,
                category='battle',
                reward_type='points',
                amount=points,
                rarity=rarity,
                description=f'Battle victory ({battle_type})',
                source='battle',
                metadata=battle_result
            )
            
            # Also award XP
            self.create_reward(
                user_id=user_id,
                category='battle',
                reward_type='xp',
                amount=points // 2,
                rarity='common',
                description=f'Battle XP reward',
                source='battle',
                metadata=battle_result
            )
            
            return reward
        else:
            # Participation reward
            return self.create_reward(
                user_id=user_id,
                category='battle',
                reward_type='points',
                amount=20,
                rarity='common',
                description=f'Battle participation ({battle_type})',
                source='battle',
                metadata=battle_result
            )
    
    # Video Generation Rewards
    def add_generation_reward(self, user_id: str, generation_result: Dict) -> Dict[str, Any]:
        """Add reward from video generation"""
        quality = generation_result.get('quality_score', 0)
        duration = generation_result.get('duration', 0)
        
        # Base reward
        base_points = 50
        quality_bonus = int(quality * 50)
        duration_bonus = min(duration // 10, 50)
        
        total_points = base_points + quality_bonus + duration_bonus
        
        rarity = 'common'
        if quality >= 0.9:
            rarity = 'epic'
        elif quality >= 0.7:
            rarity = 'rare'
        elif quality >= 0.5:
            rarity = 'uncommon'
        
        return self.create_reward(
            user_id=user_id,
            category='generation',
            reward_type='points',
            amount=total_points,
            rarity=rarity,
            description=f'Video generation reward (Quality: {quality:.2f})',
            source='video_generation',
            metadata=generation_result
        )
    
    # Level Up Rewards
    def add_level_up_reward(self, user_id: str, level: int) -> Dict[str, Any]:
        """Add reward for leveling up"""
        # Base reward
        points = level * 10
        stat_points = 5 if level % 5 == 0 else 0
        
        rewards = []
        
        # Points reward
        rewards.append(self.create_reward(
            user_id=user_id,
            category='level_up',
            reward_type='points',
            amount=points,
            rarity='uncommon',
            description=f'Level {level} reward',
            source='level_up',
            metadata={'level': level}
        ))
        
        # Stat points reward (every 5 levels)
        if stat_points > 0:
            rewards.append(self.create_reward(
                user_id=user_id,
                category='level_up',
                reward_type='stat_points',
                amount=stat_points,
                rarity='rare',
                description=f'Level {level} stat points bonus',
                source='level_up',
                metadata={'level': level}
            ))
        
        # Special rewards at milestone levels
        if level % 25 == 0:
            rewards.append(self.create_reward(
                user_id=user_id,
                category='level_up',
                reward_type='coins',
                amount=level * 10,
                rarity='epic',
                description=f'Level {level} milestone reward',
                source='level_up',
                metadata={'level': level, 'milestone': True}
            ))
        
        return {
            'success': True,
            'rewards': [r.get('reward') for r in rewards if r.get('success')]
        }
    
    # Achievement Rewards
    def add_achievement_reward(self, user_id: str, achievement_id: str, achievement_data: Dict) -> Dict[str, Any]:
        """Add reward for achievement"""
        points = achievement_data.get('points', 100)
        rarity = achievement_data.get('rarity', 'rare')
        
        return self.create_reward(
            user_id=user_id,
            category='achievement',
            reward_type='points',
            amount=points,
            rarity=rarity,
            description=f'Achievement unlocked: {achievement_data.get("name", achievement_id)}',
            source='achievement',
            metadata={'achievement_id': achievement_id, **achievement_data}
        )
    
    # Streak Rewards
    def add_streak_reward(self, user_id: str, streak_type: str, streak_count: int) -> Dict[str, Any]:
        """Add reward for streak"""
        if streak_type == 'daily':
            base_reward = 25
            bonus = min(streak_count * 5, 100)
        elif streak_type == 'battle':
            base_reward = 50
            bonus = min(streak_count * 10, 200)
        else:
            base_reward = 30
            bonus = min(streak_count * 5, 150)
        
        total_reward = base_reward + bonus
        
        rarity = 'common'
        if streak_count >= 30:
            rarity = 'epic'
        elif streak_count >= 14:
            rarity = 'rare'
        elif streak_count >= 7:
            rarity = 'uncommon'
        
        return self.create_reward(
            user_id=user_id,
            category='streak',
            reward_type='points',
            amount=total_reward,
            rarity=rarity,
            description=f'{streak_type.title()} streak reward ({streak_count} days)',
            source='streak',
            metadata={'streak_type': streak_type, 'streak_count': streak_count}
        )
    
    # Auto-reward triggers - More automatic rewards
    def trigger_activity_reward(self, user_id: str, activity_type: str, activity_data: Dict = None) -> Dict[str, Any]:
        """Trigger activity-based reward"""
        activity_data = activity_data or {}
        reward_amounts = {
            'page_view': 1,
            'click': 2,
            'scroll': 1,
            'time_30s': 5,
            'time_1m': 10,
            'time_5m': 25,
            'time_10m': 50,
            'share': 25,
            'like': 5,
            'comment': 10,
        }
        
        amount = reward_amounts.get(activity_type, 0)
        if amount > 0:
            return self.create_reward(
                user_id=user_id,
                category='activity',
                reward_type='points',
                amount=amount,
                rarity='common',
                description=f'Activity reward: {activity_type}',
                source='activity_tracking',
                metadata=activity_data
            )
        return {'success': False, 'error': 'Invalid activity type'}
    
    def trigger_discovery_reward(self, user_id: str, discovery_type: str, discovery_data: Dict = None) -> Dict[str, Any]:
        """Trigger discovery reward"""
        discovery_data = discovery_data or {}
        reward_amounts = {
            'new_feature': 50,
            'new_page': 25,
            'new_achievement': 100,
            'new_quest': 75,
            'hidden_content': 150,
            'easter_egg': 200,
        }
        
        amount = reward_amounts.get(discovery_type, 0)
        if amount > 0:
            return self.create_reward(
                user_id=user_id,
                category='discovery',
                reward_type='points',
                amount=amount,
                rarity='rare',
                description=f'Discovery reward: {discovery_type}',
                source='discovery',
                metadata=discovery_data
            )
        return {'success': False, 'error': 'Invalid discovery type'}
    
    def trigger_milestone_reward(self, user_id: str, milestone_type: str, milestone_value: int) -> Dict[str, Any]:
        """Trigger milestone reward"""
        milestone_rewards = {
            'videos_10': {'amount': 100, 'type': 'points', 'rarity': 'common'},
            'videos_50': {'amount': 500, 'type': 'points', 'rarity': 'uncommon'},
            'videos_100': {'amount': 1000, 'type': 'points', 'rarity': 'rare'},
            'videos_500': {'amount': 5000, 'type': 'points', 'rarity': 'epic'},
            'videos_1000': {'amount': 10000, 'type': 'points', 'rarity': 'legendary'},
            'battles_10': {'amount': 200, 'type': 'battle_points', 'rarity': 'common'},
            'battles_50': {'amount': 1000, 'type': 'battle_points', 'rarity': 'uncommon'},
            'battles_100': {'amount': 2500, 'type': 'battle_points', 'rarity': 'rare'},
            'level_10': {'amount': 500, 'type': 'xp', 'rarity': 'uncommon'},
            'level_25': {'amount': 1500, 'type': 'xp', 'rarity': 'rare'},
            'level_50': {'amount': 5000, 'type': 'xp', 'rarity': 'epic'},
            'level_100': {'amount': 20000, 'type': 'xp', 'rarity': 'legendary'},
        }
        
        reward_config = milestone_rewards.get(milestone_type)
        if reward_config:
            return self.create_reward(
                user_id=user_id,
                category='milestone',
                reward_type=reward_config['type'],
                amount=reward_config['amount'],
                rarity=reward_config['rarity'],
                description=f'Milestone reward: {milestone_type}',
                source='milestone',
                metadata={'milestone_type': milestone_type, 'milestone_value': milestone_value}
            )
        return {'success': False, 'error': 'Invalid milestone type'}
    
    def trigger_referral_reward(self, user_id: str, referred_user_id: str) -> Dict[str, Any]:
        """Trigger referral reward"""
        return self.create_reward(
            user_id=user_id,
            category='referral',
            reward_type='points',
            amount=100,
            rarity='rare',
            description=f'Referral reward for inviting {referred_user_id}',
            source='referral',
            metadata={'referred_user_id': referred_user_id}
        )
    
    def trigger_quality_reward(self, user_id: str, quality_score: float) -> Dict[str, Any]:
        """Trigger quality-based reward"""
        if quality_score >= 90:
            return self.create_reward(
                user_id=user_id,
                category='quality',
                reward_type='points',
                amount=500,
                rarity='epic',
                description=f'Excellent quality reward (Score: {quality_score})',
                source='quality',
                metadata={'quality_score': quality_score}
            )
        elif quality_score >= 75:
            return self.create_reward(
                user_id=user_id,
                category='quality',
                reward_type='points',
                amount=200,
                rarity='rare',
                description=f'High quality reward (Score: {quality_score})',
                source='quality',
                metadata={'quality_score': quality_score}
            )
        elif quality_score >= 60:
            return self.create_reward(
                user_id=user_id,
                category='quality',
                reward_type='points',
                amount=100,
                rarity='uncommon',
                description=f'Good quality reward (Score: {quality_score})',
                source='quality',
                metadata={'quality_score': quality_score}
            )
        return {'success': False, 'error': 'Quality score too low'}
    
    def trigger_speed_reward(self, user_id: str, completion_time: float, target_time: float) -> Dict[str, Any]:
        """Trigger speed-based reward"""
        if completion_time < target_time * 0.5:  # 50% faster
            return self.create_reward(
                user_id=user_id,
                category='speed',
                reward_type='points',
                amount=300,
                rarity='epic',
                description=f'Lightning fast completion! ({completion_time}s)',
                source='speed',
                metadata={'completion_time': completion_time, 'target_time': target_time}
            )
        elif completion_time < target_time * 0.75:  # 25% faster
            return self.create_reward(
                user_id=user_id,
                category='speed',
                reward_type='points',
                amount=150,
                rarity='rare',
                description=f'Fast completion! ({completion_time}s)',
                source='speed',
                metadata={'completion_time': completion_time, 'target_time': target_time}
            )
        return {'success': False, 'error': 'Not fast enough'}
    
    def trigger_collection_reward(self, user_id: str, collection_type: str, collection_count: int) -> Dict[str, Any]:
        """Trigger collection milestone reward"""
        if collection_count >= 100:
            return self.create_reward(
                user_id=user_id,
                category='collection',
                reward_type='badge',
                amount=None,
                rarity='legendary',
                description=f'Master Collector: {collection_count} {collection_type}',
                source='collection',
                metadata={'collection_type': collection_type, 'count': collection_count}
            )
        elif collection_count >= 50:
            return self.create_reward(
                user_id=user_id,
                category='collection',
                reward_type='badge',
                amount=None,
                rarity='epic',
                description=f'Expert Collector: {collection_count} {collection_type}',
                source='collection',
                metadata={'collection_type': collection_type, 'count': collection_count}
            )
        elif collection_count >= 25:
            return self.create_reward(
                user_id=user_id,
                category='collection',
                reward_type='points',
                amount=250,
                rarity='rare',
                description=f'Collector: {collection_count} {collection_type}',
                source='collection',
                metadata={'collection_type': collection_type, 'count': collection_count}
            )
        return {'success': False, 'error': 'Collection count too low'}
    
    def trigger_first_time_reward(self, user_id: str, action_type: str) -> Dict[str, Any]:
        """Trigger first-time action reward"""
        first_time_rewards = {
            'first_video': {'amount': 200, 'type': 'points', 'rarity': 'rare'},
            'first_battle': {'amount': 100, 'type': 'points', 'rarity': 'uncommon'},
            'first_quest': {'amount': 150, 'type': 'points', 'rarity': 'uncommon'},
            'first_share': {'amount': 50, 'type': 'points', 'rarity': 'common'},
            'first_friend': {'amount': 75, 'type': 'points', 'rarity': 'common'},
            'first_achievement': {'amount': 100, 'type': 'points', 'rarity': 'uncommon'},
        }
        
        reward_config = first_time_rewards.get(action_type)
        if reward_config:
            return self.create_reward(
                user_id=user_id,
                category='first_time',
                reward_type=reward_config['type'],
                amount=reward_config['amount'],
                rarity=reward_config['rarity'],
                description=f'First time reward: {action_type}',
                source='first_time',
                metadata={'action_type': action_type}
            )
        return {'success': False, 'error': 'Invalid first-time action'}
    
    def trigger_combo_reward(self, user_id: str, combo_type: str, combo_count: int) -> Dict[str, Any]:
        """Trigger combo reward"""
        combo_multiplier = min(combo_count / 10, 5.0)  # Max 5x multiplier
        base_reward = 50
        total_reward = int(base_reward * combo_multiplier)
        
        return self.create_reward(
            user_id=user_id,
            category='combo',
            reward_type='points',
            amount=total_reward,
            rarity='epic' if combo_count >= 50 else 'rare' if combo_count >= 20 else 'uncommon',
            description=f'Combo reward: {combo_count}x {combo_type}',
            source='combo',
            metadata={'combo_type': combo_type, 'combo_count': combo_count, 'multiplier': combo_multiplier}
        )
    
    def trigger_lucky_reward(self, user_id: str, luck_score: float) -> Dict[str, Any]:
        """Trigger lucky reward based on luck score"""
        if luck_score >= 0.9:
            return self.create_reward(
                user_id=user_id,
                category='lucky',
                reward_type='points',
                amount=1000,
                rarity='legendary',
                description='Ultra Lucky Reward!',
                source='lucky',
                metadata={'luck_score': luck_score}
            )
        elif luck_score >= 0.7:
            return self.create_reward(
                user_id=user_id,
                category='lucky',
                reward_type='points',
                amount=500,
                rarity='epic',
                description='Very Lucky Reward!',
                source='lucky',
                metadata={'luck_score': luck_score}
            )
        elif luck_score >= 0.5:
            return self.create_reward(
                user_id=user_id,
                category='lucky',
                reward_type='points',
                amount=200,
                rarity='rare',
                description='Lucky Reward!',
                source='lucky',
                metadata={'luck_score': luck_score}
            )
        return {'success': False, 'error': 'Not lucky enough'}
    
    def create_reward_bundle(self, user_id: str, bundle_name: str, bundle_items: List[Dict]) -> Dict[str, Any]:
        """Create a reward bundle with multiple rewards"""
        return self.create_reward(
            user_id=user_id,
            category='bundle',
            reward_type='bundle',
            amount=None,
            rarity='epic',
            description=f'Reward Bundle: {bundle_name}',
            source='bundle',
            metadata={'bundle_name': bundle_name, 'bundle_items': bundle_items}
        )


# Global instance
rewards_system_v2 = RewardsSystemV2()

