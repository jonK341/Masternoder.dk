"""
Hunters Game - Comprehensive Leveling System
Full-featured RPG-style leveling system with stats, titles, and rewards
"""
import math
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta, date
from collections import defaultdict


class LevelingSystem:
    """Comprehensive leveling system for Hunters Game"""
    
    def __init__(self, use_database: bool = True):
        """
        Initialize leveling system
        
        Args:
            use_database: If True, use database persistence (default: True)
        """
        self.use_database = use_database
        self.player_data = {}  # {user_id: PlayerData} - Cache
        self.xp_history = {}  # {user_id: List[XPEvent]} - Cache
        self.level_rewards = self._initialize_level_rewards()
        self.titles = self._initialize_titles()
        self.prestige_data = {}  # {user_id: PrestigeData} - Cache
        self.skill_trees = self._initialize_skill_trees()
        
    def _initialize_level_rewards(self) -> Dict[int, Dict]:
        """Initialize rewards for each level"""
        rewards = {}
        
        # Level 1-10: Novice Tier
        for level in range(1, 11):
            rewards[level] = {
                'xp_bonus_percent': 0,
                'unlock_points': level * 10,
                'stat_points': 5,
                'theme_unlocks': [],
                'template_unlocks': [],
                'title_unlock': None
            }
        
        # Level 5: Unlock batch generation
        rewards[5]['theme_unlocks'] = ['nature']
        rewards[5]['template_unlocks'] = ['basic_documentary']
        
        # Level 10: Unlock advanced features
        rewards[10]['theme_unlocks'] = ['sci-fi']
        rewards[10]['template_unlocks'] = ['advanced_documentary']
        rewards[10]['title_unlock'] = 'Apprentice Hunter'
        
        # Level 11-25: Apprentice Tier
        for level in range(11, 26):
            rewards[level] = {
                'xp_bonus_percent': 5,
                'unlock_points': level * 15,
                'stat_points': 5,
                'theme_unlocks': [],
                'template_unlocks': [],
                'title_unlock': None
            }
        
        # Level 25: Unlock custom themes
        rewards[25]['theme_unlocks'] = ['cyberpunk']
        rewards[25]['template_unlocks'] = ['professional_documentary']
        rewards[25]['title_unlock'] = 'Expert Hunter'
        
        # Level 26-50: Expert Tier
        for level in range(26, 51):
            rewards[level] = {
                'xp_bonus_percent': 10,
                'unlock_points': level * 20,
                'stat_points': 5,
                'theme_unlocks': [],
                'template_unlocks': [],
                'title_unlock': None
            }
        
        # Level 50: Unlock all features
        rewards[50]['theme_unlocks'] = ['all']
        rewards[50]['template_unlocks'] = ['all']
        rewards[50]['title_unlock'] = 'Master Hunter'
        
        # Level 51-100: Master Tier
        for level in range(51, 101):
            rewards[level] = {
                'xp_bonus_percent': 15,
                'unlock_points': level * 25,
                'stat_points': 5,
                'theme_unlocks': [],
                'template_unlocks': [],
                'title_unlock': None
            }
        
        # Level 100: Legendary status
        rewards[100]['title_unlock'] = 'Legendary Hunter'
        rewards[100]['theme_unlocks'] = ['legendary']
        rewards[100]['xp_bonus_percent'] = 25
        
        # Level 100+: Legend Tier
        for level in range(101, 201):
            rewards[level] = {
                'xp_bonus_percent': 20 + (level - 100) // 10,
                'unlock_points': level * 30,
                'stat_points': 5,
                'theme_unlocks': [],
                'template_unlocks': [],
                'title_unlock': None
            }
        
        # Special level milestones
        rewards[150]['title_unlock'] = 'Grandmaster Hunter'
        rewards[200]['title_unlock'] = 'Ultimate Hunter'
        
        return rewards
    
    def _initialize_titles(self) -> Dict[int, str]:
        """Initialize title system"""
        return {
            1: 'Novice Hunter',
            10: 'Apprentice Hunter',
            25: 'Expert Hunter',
            50: 'Master Hunter',
            100: 'Legendary Hunter',
            150: 'Grandmaster Hunter',
            200: 'Ultimate Hunter'
        }
    
    def _initialize_skill_trees(self) -> Dict[str, Dict]:
        """Initialize skill trees for hunter game"""
        return {
            'combat': {
                'name': 'Combat Skills',
                'skills': {
                    'precision_strike': {
                        'name': 'Precision Strike',
                        'description': 'Increases critical hit chance by 5%',
                        'max_level': 10,
                        'cost_per_level': 5,
                        'prerequisites': [],
                        'bonus_per_level': {'critical_chance': 0.5}
                    },
                    'weapon_mastery': {
                        'name': 'Weapon Mastery',
                        'description': 'Increases damage by 2% per level',
                        'max_level': 20,
                        'cost_per_level': 3,
                        'prerequisites': ['precision_strike'],
                        'bonus_per_level': {'damage_multiplier': 0.02}
                    },
                    'defensive_stance': {
                        'name': 'Defensive Stance',
                        'description': 'Reduces incoming damage by 3% per level',
                        'max_level': 15,
                        'cost_per_level': 4,
                        'prerequisites': [],
                        'bonus_per_level': {'damage_reduction': 0.03}
                    }
                }
            },
            'hunting': {
                'name': 'Hunting Skills',
                'skills': {
                    'tracking': {
                        'name': 'Tracking',
                        'description': 'Increases XP gain from hunts by 5% per level',
                        'max_level': 10,
                        'cost_per_level': 5,
                        'prerequisites': [],
                        'bonus_per_level': {'xp_bonus': 0.05}
                    },
                    'beast_mastery': {
                        'name': 'Beast Mastery',
                        'description': 'Unlocks rare creature encounters',
                        'max_level': 5,
                        'cost_per_level': 10,
                        'prerequisites': ['tracking'],
                        'bonus_per_level': {'rare_encounter_chance': 0.1}
                    },
                    'survival_instinct': {
                        'name': 'Survival Instinct',
                        'description': 'Increases health regeneration',
                        'max_level': 10,
                        'cost_per_level': 4,
                        'prerequisites': [],
                        'bonus_per_level': {'health_regen': 0.5}
                    }
                }
            },
            'crafting': {
                'name': 'Crafting Skills',
                'skills': {
                    'weapon_crafting': {
                        'name': 'Weapon Crafting',
                        'description': 'Allows crafting of better weapons',
                        'max_level': 10,
                        'cost_per_level': 6,
                        'prerequisites': [],
                        'bonus_per_level': {'craft_quality': 0.1}
                    },
                    'armor_crafting': {
                        'name': 'Armor Crafting',
                        'description': 'Allows crafting of better armor',
                        'max_level': 10,
                        'cost_per_level': 6,
                        'prerequisites': [],
                        'bonus_per_level': {'armor_quality': 0.1}
                    },
                    'enchanting': {
                        'name': 'Enchanting',
                        'description': 'Adds special effects to items',
                        'max_level': 5,
                        'cost_per_level': 15,
                        'prerequisites': ['weapon_crafting', 'armor_crafting'],
                        'bonus_per_level': {'enchant_power': 0.2}
                    }
                }
            }
        }
    
    def calculate_level(self, total_xp: int) -> int:
        """
        Calculate level from total XP
        
        Formula:
        Level 1-10:   Base XP = 1000 * level
        Level 11-25:  Base XP = 2000 * level
        Level 26-50:  Base XP = 3000 * level
        Level 51-100: Base XP = 5000 * level
        Level 100+:   Base XP = 10000 * level
        """
        if total_xp < 55000:  # Level 1-10 (0-55k XP)
            return min(10, (total_xp // 1000) + 1)
        elif total_xp < 500000:  # Level 11-25 (55k-500k XP)
            return min(25, 10 + ((total_xp - 55000) // 2000) + 1)
        elif total_xp < 2000000:  # Level 26-50 (500k-2M XP)
            return min(50, 25 + ((total_xp - 500000) // 3000) + 1)
        elif total_xp < 10000000:  # Level 51-100 (2M-10M XP)
            return min(100, 50 + ((total_xp - 2000000) // 5000) + 1)
        else:  # Level 100+ (10M+ XP)
            return 100 + ((total_xp - 10000000) // 10000) + 1
    
    def xp_for_level(self, level: int) -> int:
        """Calculate total XP needed for a specific level"""
        if level <= 1:
            return 0
        elif level <= 10:
            return (level - 1) * 1000
        elif level <= 25:
            return 55000 + (level - 10) * 2000
        elif level <= 50:
            return 500000 + (level - 25) * 3000
        elif level <= 100:
            return 2000000 + (level - 50) * 5000
        else:
            return 10000000 + (level - 100) * 10000
    
    def xp_to_next_level(self, current_level: int, current_xp: int) -> int:
        """Calculate XP needed to reach next level"""
        next_level = current_level + 1
        xp_for_next = self.xp_for_level(next_level)
        return max(0, xp_for_next - current_xp)
    
    def get_level_progress(self, current_level: int, current_xp: int) -> float:
        """Calculate progress percentage to next level"""
        xp_for_current = self.xp_for_level(current_level)
        xp_for_next = self.xp_for_level(current_level + 1)
        xp_in_level = current_xp - xp_for_current
        xp_needed = xp_for_next - xp_for_current
        
        if xp_needed == 0:
            return 100.0
        
        return min(100.0, (xp_in_level / xp_needed) * 100)
    
    def get_title_for_level(self, level: int) -> str:
        """Get title for a specific level"""
        # Find highest title for this level
        titles = sorted([l for l in self.titles.keys() if l <= level], reverse=True)
        if titles:
            return self.titles[titles[0]]
        return 'Novice Hunter'
    
    def _calculate_xp_multipliers(self, user_id: str, action_type: str = None) -> Dict[str, Any]:
        """Calculate XP multipliers from prestige, skill trees, and other bonuses"""
        multipliers = {
            'prestige': 1.0,
            'skill_tree': 1.0,
            'level_bonus': 1.0,
            'total_multiplier': 1.0
        }
        
        if user_id not in self.player_data:
            return multipliers
        
        player = self.player_data[user_id]
        
        # Prestige bonus
        prestige_level = player.get('prestige_level', 0)
        if prestige_level > 0:
            multipliers['prestige'] = 1.0 + (prestige_level * 0.1)  # +10% per prestige
        
        # Skill tree bonuses
        player_skills = player.get('skills', {})
        for tree_name, tree_skills in player_skills.items():
            for skill_id, skill_data in tree_skills.items():
                if skill_data.get('unlocked', False):
                    level = skill_data.get('level', 0)
                    if tree_name in self.skill_trees and skill_id in self.skill_trees[tree_name]['skills']:
                        skill = self.skill_trees[tree_name]['skills'][skill_id]
                        bonus_per_level = skill.get('bonus_per_level', {})
                        if 'xp_bonus' in bonus_per_level:
                            multipliers['skill_tree'] += bonus_per_level['xp_bonus'] * level
        
        # Level bonus (from level rewards)
        current_level = player.get('current_level', 1)
        if current_level in self.level_rewards:
            level_reward = self.level_rewards[current_level]
            xp_bonus_percent = level_reward.get('xp_bonus_percent', 0)
            if xp_bonus_percent > 0:
                multipliers['level_bonus'] = 1.0 + (xp_bonus_percent / 100)
        
        # Calculate total multiplier
        multipliers['total_multiplier'] = multipliers['prestige'] * multipliers['skill_tree'] * multipliers['level_bonus']
        
        return multipliers
    
    def award_xp(self, user_id: str, xp_amount: int, source: str, 
                 action_type: str = None, metadata: Dict = None) -> Dict[str, Any]:
        """
        Award XP to a player and check for level up
        Enhanced with unified point system integration
        
        Returns:
            Dict with level_up info, new level, rewards, etc.
        """
        # Apply multipliers from skill trees and prestige
        multipliers = self._calculate_xp_multipliers(user_id, action_type)
        final_xp = int(xp_amount * multipliers['total_multiplier'])
        
        # Award points through unified point system
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                user_id, 
                'xp_points', 
                final_xp,
                source=f'hunter_game_{source}',
                metadata={
                    'action_type': action_type,
                    'base_xp': xp_amount,
                    'multipliers': multipliers,
                    'final_xp': final_xp,
                    **(metadata or {})
                }
            )
        except Exception as e:
            print(f"[HuntersLeveling] Warning: Could not award unified points: {e}")
        
        # Load player from database if not in cache
        if user_id not in self.player_data:
            db_player = self._load_player_from_db(user_id)
            if db_player:
                self.player_data[user_id] = db_player
            else:
                self._initialize_player(user_id)
        
        player = self.player_data[user_id]
        old_level = player['current_level']
        
        # Apply XP bonus if active
        xp_bonus = player.get('xp_bonus_percent', 0)
        if xp_bonus > 0:
            xp_amount = int(xp_amount * (1 + xp_bonus / 100))
            # Decrease bonus
            player['xp_bonus_remaining'] = max(0, player.get('xp_bonus_remaining', 0) - 1)
            if player['xp_bonus_remaining'] == 0:
                player['xp_bonus_percent'] = 0
        
        # Add XP
        player['total_xp'] += xp_amount
        player['current_xp'] = player['total_xp']
        
        # Recalculate level
        new_level = self.calculate_level(player['total_xp'])
        player['current_level'] = new_level
        
        # Update level info
        player['xp_to_next_level'] = self.xp_to_next_level(new_level, player['total_xp'])
        player['level_progress'] = self.get_level_progress(new_level, player['total_xp'])
        player['title'] = self.get_title_for_level(new_level)
        
        # Record XP event
        if user_id not in self.xp_history:
            self.xp_history[user_id] = []
        
        xp_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'xp_amount': xp_amount,
            'source': source,
            'action_type': action_type,
            'metadata': metadata or {},
            'level_before': old_level,
            'level_after': new_level
        }
        
        self.xp_history[user_id].append(xp_event)
        
        # Save XP event to database
        self._save_xp_event_to_db(user_id, xp_event)
        
        # Check for level up
        level_up_info = None
        if new_level > old_level:
            level_up_info = self._handle_level_up(user_id, old_level, new_level)
        
        # Save player to database
        self._save_player_to_db(user_id, player)
        
        return {
            'user_id': user_id,
            'xp_awarded': xp_amount,
            'total_xp': player['total_xp'],
            'current_level': new_level,
            'level_up': level_up_info is not None,
            'level_up_info': level_up_info,
            'xp_to_next_level': player['xp_to_next_level'],
            'level_progress': player['level_progress'],
            'title': player['title']
        }
    
    def _handle_level_up(self, user_id: str, old_level: int, new_level: int) -> Dict[str, Any]:
        """Handle level up and grant rewards"""
        player = self.player_data[user_id]
        rewards_granted = []
        stat_points_gained = 0
        themes_unlocked = []
        templates_unlocked = []
        title_unlocked = None
        
        # Grant rewards for each level gained
        for level in range(old_level + 1, new_level + 1):
            if level in self.level_rewards:
                reward = self.level_rewards[level]
                
                # Stat points
                stat_points_gained += reward.get('stat_points', 5)
                player['available_stat_points'] = player.get('available_stat_points', 0) + reward.get('stat_points', 5)
                
                # Theme unlocks
                if reward.get('theme_unlocks'):
                    themes_unlocked.extend(reward['theme_unlocks'])
                    if 'unlocked_themes' not in player:
                        player['unlocked_themes'] = []
                    player['unlocked_themes'].extend(reward['theme_unlocks'])
                
                # Template unlocks
                if reward.get('template_unlocks'):
                    templates_unlocked.extend(reward['template_unlocks'])
                    if 'unlocked_templates' not in player:
                        player['unlocked_templates'] = []
                    player['unlocked_templates'].extend(reward['template_unlocks'])
                
                # Title unlock
                if reward.get('title_unlock'):
                    title_unlocked = reward['title_unlock']
                    player['title'] = title_unlocked
                
                # XP bonus
                if reward.get('xp_bonus_percent', 0) > 0:
                    player['xp_bonus_percent'] = reward['xp_bonus_percent']
                    player['xp_bonus_remaining'] = 10  # 10 actions
        
        return {
            'old_level': old_level,
            'new_level': new_level,
            'stat_points_gained': stat_points_gained,
            'themes_unlocked': themes_unlocked,
            'templates_unlocked': templates_unlocked,
            'title_unlocked': title_unlocked,
            'rewards': rewards_granted
        }
    
    def _initialize_player(self, user_id: str):
        """Initialize a new player (in-memory and optionally in database)"""
        player_data = {
            'user_id': user_id,
            'current_level': 1,
            'current_xp': 0,
            'total_xp': 0,
            'xp_to_next_level': 1000,
            'level_progress': 0.0,
            'title': 'Novice Hunter',
            'prestige_level': 0,
            'stat_creativity': 0,
            'stat_efficiency': 0,
            'stat_quality': 0,
            'stat_social': 0,
            'stat_knowledge': 0,
            'available_stat_points': 0,
            'unlocked_themes': [],
            'unlocked_templates': [],
            'xp_bonus_percent': 0,
            'xp_bonus_remaining': 0,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        
        self.player_data[user_id] = player_data
        
        # Save to database if enabled (will be saved when XP is awarded)
        # Initialization just creates in-memory structure
        
        return player_data
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get user stats including stats points
        Returns stats points total, available, used, and individual stat categories
        """
        if user_id not in self.player_data:
            if self.use_database:
                db_player = self._load_player_from_db(user_id)
                if db_player:
                    self.player_data[user_id] = db_player
                else:
                    self._initialize_player(user_id)
            else:
                self._initialize_player(user_id)
        
        player = self.player_data[user_id]
        
        # Calculate stats points
        stats_points_total = player.get('stats_points_total', 0)
        stats_points_used = sum([
            player.get('creativity_points', 0),
            player.get('efficiency_points', 0),
            player.get('quality_points', 0),
            player.get('social_points', 0),
            player.get('knowledge_points', 0)
        ])
        stats_points_available = stats_points_total - stats_points_used
        
        return {
            'level': player.get('current_level', 1),
            'total_xp': player.get('total_xp', 0),
            'stats_points_total': stats_points_total,
            'stats_points_available': max(0, stats_points_available),
            'stats_points_used': stats_points_used,
            'creativity_points': player.get('creativity_points', 0),
            'efficiency_points': player.get('efficiency_points', 0),
            'quality_points': player.get('quality_points', 0),
            'social_points': player.get('social_points', 0),
            'knowledge_points': player.get('knowledge_points', 0),
            'prestige_level': player.get('prestige_level', 0),
            'title': player.get('current_title', 'Novice Hunter')
        }
    
    def _get_user_stats_internal(self, user_id: str) -> Dict[str, Any]:
        """Internal method that calls get_user_stats for backward compatibility"""
        return self.get_user_stats(user_id)
    
    def _load_player_from_db(self, user_id: str) -> Optional[Dict]:
        """Load player data from database"""
        if not self.use_database:
            return None
        
        try:
            from src.db.models import db, PlayerLevel
            from flask import current_app
            
            try:
                # Try to get app context
                app_context = current_app.app_context()
            except RuntimeError:
                # No app context available, return None (will use in-memory)
                return None
            
            with app_context:
                player = PlayerLevel.query.get(user_id)
                if player:
                    return {
                        'user_id': player.user_id,
                        'current_level': player.current_level,
                        'current_xp': player.current_xp,
                        'total_xp': player.total_xp,
                        'xp_to_next_level': player.xp_to_next_level,
                        'level_progress': float(player.level_progress),
                        'title': player.title,
                        'prestige_level': player.prestige_level,
                        'stat_creativity': player.stat_creativity,
                        'stat_efficiency': player.stat_efficiency,
                        'stat_quality': player.stat_quality,
                        'stat_social': player.stat_social,
                        'stat_knowledge': player.stat_knowledge,
                        'available_stat_points': player.available_stat_points,
                        'unlocked_themes': json.loads(player.unlocked_themes) if player.unlocked_themes else [],
                        'unlocked_templates': json.loads(player.unlocked_templates) if player.unlocked_templates else [],
                        'xp_bonus_percent': player.xp_bonus_percent,
                        'xp_bonus_remaining': player.xp_bonus_remaining,
                        'prestige_xp_bonus': player.prestige_xp_bonus,
                        'created_at': player.created_at.isoformat() if player.created_at else None,
                        'updated_at': player.updated_at.isoformat() if player.updated_at else None
                    }
        except Exception as e:
            print(f"[LevelingSystem] Could not load from database: {e}")
        
        return None
    
    def _save_player_to_db(self, user_id: str, player_data: Dict):
        """Save player data to database"""
        if not self.use_database:
            return
        
        try:
            from src.db.models import db, PlayerLevel
            from flask import current_app
            
            try:
                # Try to get app context
                app_context = current_app.app_context()
            except RuntimeError:
                # No app context available, skip database save
                return
            
            with app_context:
                player = PlayerLevel.query.get(user_id)
                if player:
                    # Update existing player
                    player.current_level = player_data.get('current_level', 1)
                    player.current_xp = player_data.get('current_xp', 0)
                    player.total_xp = player_data.get('total_xp', 0)
                    player.xp_to_next_level = player_data.get('xp_to_next_level', 1000)
                    player.level_progress = player_data.get('level_progress', 0.0)
                    player.title = player_data.get('title', 'Novice Hunter')
                    player.prestige_level = player_data.get('prestige_level', 0)
                    player.stat_creativity = player_data.get('stat_creativity', 0)
                    player.stat_efficiency = player_data.get('stat_efficiency', 0)
                    player.stat_quality = player_data.get('stat_quality', 0)
                    player.stat_social = player_data.get('stat_social', 0)
                    player.stat_knowledge = player_data.get('stat_knowledge', 0)
                    player.available_stat_points = player_data.get('available_stat_points', 0)
                    player.unlocked_themes = json.dumps(player_data.get('unlocked_themes', []))
                    player.unlocked_templates = json.dumps(player_data.get('unlocked_templates', []))
                    player.xp_bonus_percent = player_data.get('xp_bonus_percent', 0)
                    player.xp_bonus_remaining = player_data.get('xp_bonus_remaining', 0)
                    player.prestige_xp_bonus = player_data.get('prestige_xp_bonus', 0)
                    player.updated_at = datetime.utcnow()
                else:
                    # Create new player
                    player = PlayerLevel(
                        user_id=user_id,
                        current_level=player_data.get('current_level', 1),
                        current_xp=player_data.get('current_xp', 0),
                        total_xp=player_data.get('total_xp', 0),
                        xp_to_next_level=player_data.get('xp_to_next_level', 1000),
                        level_progress=player_data.get('level_progress', 0.0),
                        title=player_data.get('title', 'Novice Hunter'),
                        prestige_level=player_data.get('prestige_level', 0),
                        stat_creativity=player_data.get('stat_creativity', 0),
                        stat_efficiency=player_data.get('stat_efficiency', 0),
                        stat_quality=player_data.get('stat_quality', 0),
                        stat_social=player_data.get('stat_social', 0),
                        stat_knowledge=player_data.get('stat_knowledge', 0),
                        available_stat_points=player_data.get('available_stat_points', 0),
                        unlocked_themes=json.dumps(player_data.get('unlocked_themes', [])),
                        unlocked_templates=json.dumps(player_data.get('unlocked_templates', [])),
                        xp_bonus_percent=player_data.get('xp_bonus_percent', 0),
                        xp_bonus_remaining=player_data.get('xp_bonus_remaining', 0),
                        prestige_xp_bonus=player_data.get('prestige_xp_bonus', 0)
                    )
                    db.session.add(player)
                
                db.session.commit()
        except Exception as e:
            print(f"[LevelingSystem] Could not save to database: {e}")
    
    def _save_xp_event_to_db(self, user_id: str, xp_event: Dict):
        """Save XP event to database"""
        if not self.use_database:
            return
        
        try:
            from src.db.models import db, XPHistory
            from flask import current_app
            
            try:
                # Try to get app context
                app_context = current_app.app_context()
            except RuntimeError:
                # No app context available, skip database save
                return
            
            with app_context:
                event = XPHistory(
                    user_id=user_id,
                    xp_amount=xp_event.get('xp_amount', 0),
                    source=xp_event.get('source', 'unknown'),
                    action_type=xp_event.get('action_type'),
                    event_metadata=json.dumps(xp_event.get('metadata', {})),
                    level_before=xp_event.get('level_before'),
                    level_after=xp_event.get('level_after')
                )
                db.session.add(event)
                db.session.commit()
        except Exception as e:
            print(f"[LevelingSystem] Could not save XP event to database: {e}")
    
    def get_player_profile(self, user_id: str) -> Dict[str, Any]:
        """Get complete player profile"""
        # Load from database if not in cache
        if user_id not in self.player_data:
            db_player = self._load_player_from_db(user_id)
            if db_player:
                self.player_data[user_id] = db_player
            else:
                self._initialize_player(user_id)
        
        player = self.player_data[user_id]
        
        # Get next level info
        next_level = player['current_level'] + 1
        xp_for_next = self.xp_for_level(next_level)
        xp_for_current = self.xp_for_level(player['current_level'])
        
        return {
            'user_id': user_id,
            'current_level': player['current_level'],
            'current_xp': player['current_xp'],
            'total_xp': player['total_xp'],
            'xp_to_next_level': player['xp_to_next_level'],
            'level_progress': player['level_progress'],
            'title': player['title'],
            'prestige_level': player.get('prestige_level', 0),
            'stats': {
                'creativity': player.get('stat_creativity', 0),
                'efficiency': player.get('stat_efficiency', 0),
                'quality': player.get('stat_quality', 0),
                'social': player.get('stat_social', 0),
                'knowledge': player.get('stat_knowledge', 0)
            },
            'available_stat_points': player.get('available_stat_points', 0),
            'unlocked_themes': player.get('unlocked_themes', []),
            'unlocked_templates': player.get('unlocked_templates', []),
            'xp_bonus': {
                'percent': player.get('xp_bonus_percent', 0),
                'remaining_actions': player.get('xp_bonus_remaining', 0)
            },
            'next_level_info': {
                'level': next_level,
                'xp_required': xp_for_next - xp_for_current,
                'title': self.get_title_for_level(next_level),
                'rewards': self.level_rewards.get(next_level, {})
            }
        }
    
    def allocate_stat_points(self, user_id: str, stat_allocations: Dict[str, int]) -> Dict[str, Any]:
        """
        Allocate stat points
        
        Args:
            user_id: Player ID
            stat_allocations: Dict with stat names and points to allocate
                e.g., {'creativity': 5, 'efficiency': 3}
        """
        # Load from database if not in cache
        if user_id not in self.player_data:
            db_player = self._load_player_from_db(user_id)
            if db_player:
                self.player_data[user_id] = db_player
            else:
                self._initialize_player(user_id)
        
        player = self.player_data[user_id]
        available = player.get('available_stat_points', 0)
        
        total_to_allocate = sum(stat_allocations.values())
        if total_to_allocate > available:
            return {
                'success': False,
                'error': f'Not enough stat points. Available: {available}, Requested: {total_to_allocate}'
            }
        
        # Validate stat names
        valid_stats = ['creativity', 'efficiency', 'quality', 'social', 'knowledge']
        for stat_name in stat_allocations.keys():
            if stat_name not in valid_stats:
                return {
                    'success': False,
                    'error': f'Invalid stat name: {stat_name}'
                }
        
        # Allocate stats
        for stat_name, points in stat_allocations.items():
            current_stat = player.get(f'stat_{stat_name}', 0)
            new_stat = min(100, current_stat + points)  # Max 100
            player[f'stat_{stat_name}'] = new_stat
        
        player['available_stat_points'] -= total_to_allocate
        player['updated_at'] = datetime.utcnow().isoformat()
        
        # Save to database
        self._save_player_to_db(user_id, player)
        
        return {
            'success': True,
            'allocated': stat_allocations,
            'remaining_points': player['available_stat_points'],
            'new_stats': {
                stat: player.get(f'stat_{stat}', 0)
                for stat in valid_stats
            }
        }
    
    def track_agent_xp(self, user_id: str, agent_id: str, xp_amount: int, 
                      activity_type: str = 'hunter_activity', metadata: Dict = None) -> Dict[str, Any]:
        """
        Track XP for hunter game activities with agent integration
        Awards XP to both user and agent
        """
        try:
            from backend.services.agent_system import agent_system
            
            # Get agent
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {'error': 'Agent not found'}
            
            # Calculate agent skill bonuses
            agent_bonuses = self._calculate_agent_skill_bonuses(agent, activity_type)
            
            # Apply bonuses to XP
            bonus_multiplier = 1.0 + (agent_bonuses.get('xp_bonus_percent', 0) / 100.0)
            adjusted_xp = int(xp_amount * bonus_multiplier)
            
            # Award XP to user (hunter game)
            user_result = self.award_xp(
                user_id, 
                adjusted_xp, 
                f'agent_{agent_id}_{activity_type}',
                activity_type,
                {**(metadata or {}), 'agent_id': agent_id, 'agent_bonuses': agent_bonuses}
            )
            
            # Award XP to agent
            agent_xp = int(xp_amount * 0.3)  # Agent gets 30% of XP
            agent_result = agent_system.award_xp(agent_id, 'system_1', agent_xp)
            
            # Save activity to agent's visual memory
            try:
                agent_system.save_visual_memory(agent_id, 'hunter_activity', {
                    'user_id': user_id,
                    'activity_type': activity_type,
                    'xp_awarded': adjusted_xp,
                    'agent_xp_awarded': agent_xp,
                    'bonuses_applied': agent_bonuses,
                    'timestamp': datetime.utcnow().isoformat()
                })
            except:
                pass
            
            return {
                'success': True,
                'user_id': user_id,
                'agent_id': agent_id,
                'base_xp': xp_amount,
                'adjusted_xp': adjusted_xp,
                'agent_xp': agent_xp,
                'agent_bonuses': agent_bonuses,
                'user_result': user_result,
                'agent_result': agent_result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_agent_skill_bonuses(self, agent: Dict, activity_type: str) -> Dict[str, Any]:
        """Calculate skill bonuses from agent for hunter activities"""
        bonuses = {
            'xp_bonus_percent': 0,
            'stat_bonus_percent': 0,
            'reward_bonus_percent': 0,
            'skill_names': []
        }
        
        # Get agent skills
        agent_skills = agent.get('top50_skills', [])
        
        # Check for relevant skills
        hunter_skills = [s for s in agent_skills if 'hunter' in s.get('name', '').lower() or 
                        'leveling' in s.get('name', '').lower() or
                        'xp' in s.get('name', '').lower()]
        
        # Calculate bonuses from skills
        for skill in hunter_skills:
            skill_level = skill.get('level', 1)
            skill_name = skill.get('name', '')
            
            bonuses['xp_bonus_percent'] += skill_level * 0.5  # 0.5% per skill level
            bonuses['stat_bonus_percent'] += skill_level * 0.3  # 0.3% per skill level
            bonuses['skill_names'].append(skill_name)
        
        # Check agent level for additional bonuses
        agent_level = agent.get('level_system_1', 1)
        if agent_level > 10:
            bonuses['xp_bonus_percent'] += (agent_level - 10) * 0.2  # 0.2% per level above 10
        if agent_level > 25:
            bonuses['reward_bonus_percent'] += 5  # 5% bonus at level 25+
        if agent_level > 50:
            bonuses['reward_bonus_percent'] += 10  # Additional 10% at level 50+
        
        # Check for special trophies
        agent_trophies = agent.get('special_trophies', [])
        for trophy in agent_trophies:
            if 'hunter' in trophy.get('name', '').lower() or 'leveling' in trophy.get('name', '').lower():
                bonuses['xp_bonus_percent'] += 5  # 5% bonus per relevant trophy
        
        return bonuses
    
    def get_agent_recommendations(self, user_id: str, agent_id: str) -> Dict[str, Any]:
        """
        Get agent recommendations for hunter game activities
        """
        try:
            from backend.services.agent_system import agent_system
            
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {'error': 'Agent not found'}
            
            # Get user stats
            user_stats = self.get_user_stats(user_id)
            current_level = user_stats.get('level', 1)
            current_xp = user_stats.get('total_xp', 0)
            xp_to_next = self.xp_to_next_level(current_level, current_xp)
            
            # Get agent's hunter-related memories
            agent_memories = agent.get('visual_memory', [])
            hunter_memories = [m for m in agent_memories if m.get('category') == 'hunter_activity']
            
            # Analyze agent's recommendations
            recommendations = []
            
            # Recommendation 1: XP goals
            if xp_to_next > 0:
                recommendations.append({
                    'type': 'xp_goal',
                    'title': 'Reach Next Level',
                    'description': f"You need {xp_to_next:,} XP to reach level {current_level + 1}.",
                    'action': f'Complete activities to earn {xp_to_next:,} XP',
                    'priority': 'high',
                    'expected_xp': xp_to_next
                })
            
            # Recommendation 2: Agent skill development
            agent_skills = agent.get('top50_skills', [])
            hunter_skills = [s for s in agent_skills if 'hunter' in s.get('name', '').lower()]
            if len(hunter_skills) < 3:
                recommendations.append({
                    'type': 'agent_skills',
                    'title': 'Develop Agent Hunter Skills',
                    'description': f"Your agent has {len(hunter_skills)} hunter skills. Develop more for better bonuses.",
                    'action': 'Train agent in hunter-related activities',
                    'priority': 'medium',
                    'expected_benefit': 'Up to 15% XP bonus'
                })
            
            # Recommendation 3: Activity focus
            if hunter_memories:
                # Analyze which activities gave most XP
                activity_xp = {}
                for memory in hunter_memories[-20:]:
                    activity_type = memory.get('data', {}).get('activity_type', 'unknown')
                    xp = memory.get('data', {}).get('xp_awarded', 0)
                    if activity_type not in activity_xp:
                        activity_xp[activity_type] = []
                    activity_xp[activity_type].append(xp)
                
                best_activity = max(activity_xp.items(), key=lambda x: sum(x[1]) / len(x[1]), default=(None, []))
                if best_activity[0]:
                    recommendations.append({
                        'type': 'activity_focus',
                        'title': 'Focus on Best Activity',
                        'description': f"Your agent found that {best_activity[0]} activities give the best XP rewards.",
                        'action': f'Focus on {best_activity[0]} activities',
                        'priority': 'medium',
                        'expected_benefit': f'Average {int(sum(best_activity[1]) / len(best_activity[1]))} XP per activity'
                    })
            
            # Recommendation 4: Level milestones
            next_milestone = self._get_next_milestone(current_level)
            if next_milestone:
                xp_to_milestone = self.xp_for_level(next_milestone) - current_xp
                recommendations.append({
                    'type': 'milestone',
                    'title': f'Reach Level {next_milestone} Milestone',
                    'description': f"Level {next_milestone} unlocks special rewards and bonuses.",
                    'action': f'Earn {xp_to_milestone:,} XP to reach milestone',
                    'priority': 'high',
                    'expected_rewards': self.level_rewards.get(next_milestone, {})
                })
            
            # Get agent's smart recommendations
            agent_recommendations = agent_system.get_smart_recommendations(agent_id, 'hunter_game')
            
            return {
                'success': True,
                'user_id': user_id,
                'agent_id': agent_id,
                'current_level': current_level,
                'current_xp': current_xp,
                'xp_to_next_level': xp_to_next,
                'recommendations': recommendations,
                'agent_recommendations': agent_recommendations.get('recommendations', []),
                'agent_hunter_experience': len(hunter_memories),
                'agent_bonuses_available': self._calculate_agent_skill_bonuses(agent, 'hunter_activity')
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_next_milestone(self, current_level: int) -> Optional[int]:
        """Get next milestone level"""
        milestones = [10, 25, 50, 100, 150, 200]
        for milestone in milestones:
            if current_level < milestone:
                return milestone
        return None
    
    def apply_agent_skill_bonuses(self, user_id: str, agent_id: str, base_xp: int) -> Dict[str, Any]:
        """
        Apply agent skill bonuses to XP calculation
        """
        try:
            from backend.services.agent_system import agent_system
            
            agent = agent_system.get_agent(agent_id)
            if not agent:
                return {
                    'success': False,
                    'error': 'Agent not found',
                    'base_xp': base_xp,
                    'final_xp': base_xp
                }
            
            # Calculate bonuses
            bonuses = self._calculate_agent_skill_bonuses(agent, 'hunter_activity')
            
            # Apply bonuses
            xp_multiplier = 1.0 + (bonuses.get('xp_bonus_percent', 0) / 100.0)
            final_xp = int(base_xp * xp_multiplier)
            bonus_xp = final_xp - base_xp
            
            return {
                'success': True,
                'user_id': user_id,
                'agent_id': agent_id,
                'base_xp': base_xp,
                'bonus_xp': bonus_xp,
                'final_xp': final_xp,
                'bonuses': bonuses,
                'multiplier': xp_multiplier
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'base_xp': base_xp,
                'final_xp': base_xp
            }
    
    def get_leaderboard(self, limit: int = 100, category: str = 'level') -> List[Dict[str, Any]]:
        """
        Get leaderboard
        
        Args:
            limit: Number of players to return
            category: 'level', 'xp', 'achievements'
        """
        # Load from database if enabled
        if self.use_database:
            try:
                from src.db.models import db, PlayerLevel
                from flask import current_app
                
                try:
                    # Try to get app context
                    app_context = current_app.app_context()
                except RuntimeError:
                    # No app context, fallback to in-memory
                    app_context = None
                
                if app_context:
                    with app_context:
                        if category == 'level':
                            players_db = PlayerLevel.query.order_by(
                                PlayerLevel.current_level.desc(),
                                PlayerLevel.total_xp.desc()
                            ).limit(limit).all()
                        elif category == 'xp':
                            players_db = PlayerLevel.query.order_by(
                                PlayerLevel.total_xp.desc()
                            ).limit(limit).all()
                        else:
                            players_db = PlayerLevel.query.order_by(
                                PlayerLevel.current_level.desc()
                            ).limit(limit).all()
                        
                        leaderboard = []
                        for rank, player in enumerate(players_db, 1):
                            leaderboard.append({
                                'rank': rank,
                                'user_id': player.user_id,
                                'level': player.current_level,
                                'total_xp': player.total_xp,
                                'title': player.title
                            })
                        
                        return leaderboard
            except Exception as e:
                print(f"[LevelingSystem] Could not load leaderboard from database: {e}")
        
        # Fallback to in-memory
        players = list(self.player_data.values())
        
        if category == 'level':
            players.sort(key=lambda p: (p.get('current_level', 1), p.get('total_xp', 0)), reverse=True)
        elif category == 'xp':
            players.sort(key=lambda p: p.get('total_xp', 0), reverse=True)
        elif category == 'achievements':
            # Would need to integrate with achievement system
            players.sort(key=lambda p: p.get('current_level', 1), reverse=True)
        
        leaderboard = []
        for rank, player in enumerate(players[:limit], 1):
            leaderboard.append({
                'rank': rank,
                'user_id': player['user_id'],
                'level': player.get('current_level', 1),
                'total_xp': player.get('total_xp', 0),
                'title': player.get('title', 'Novice Hunter')
            })
        
        return leaderboard
    
    def calculate_xp_requirements(self, target_level: int, current_level: int = 1, 
                                 current_xp: int = 0) -> Dict[str, Any]:
        """
        Calculate XP requirements to reach a target level
        """
        if target_level <= current_level:
            return {
                'success': False,
                'error': 'Target level must be higher than current level'
            }
        
        # Calculate total XP needed
        xp_for_target = self.xp_for_level(target_level)
        xp_for_current = self.xp_for_level(current_level)
        xp_needed = xp_for_target - current_xp
        
        # Calculate levels to gain
        levels_to_gain = target_level - current_level
        
        # Calculate XP per level (average)
        avg_xp_per_level = xp_needed / levels_to_gain if levels_to_gain > 0 else 0
        
        # Break down by level ranges
        breakdown = []
        for level in range(current_level + 1, target_level + 1):
            level_xp = self.xp_for_level(level) - self.xp_for_level(level - 1)
            breakdown.append({
                'level': level,
                'xp_required': level_xp,
                'cumulative_xp': self.xp_for_level(level) - current_xp
            })
        
        return {
            'success': True,
            'current_level': current_level,
            'current_xp': current_xp,
            'target_level': target_level,
            'xp_needed': xp_needed,
            'levels_to_gain': levels_to_gain,
            'average_xp_per_level': round(avg_xp_per_level, 2),
            'breakdown': breakdown
        }
    
    def calculate_level_progression(self, user_id: str, days: int = 7, 
                                   daily_xp: int = None) -> Dict[str, Any]:
        """
        Calculate level progression predictions
        """
        user_stats = self.get_user_stats(user_id)
        current_level = user_stats.get('level', 1)
        current_xp = user_stats.get('total_xp', 0)
        
        # Estimate daily XP if not provided
        if daily_xp is None:
            # Get recent XP history
            recent_xp = self.xp_history.get(user_id, [])
            if recent_xp:
                # Calculate average daily XP from last 7 days
                from datetime import datetime, timedelta
                cutoff = datetime.utcnow() - timedelta(days=7)
                recent = [x for x in recent_xp if datetime.fromisoformat(x.get('timestamp', '')) > cutoff]
                if recent:
                    total_recent_xp = sum(x.get('xp_amount', 0) for x in recent)
                    daily_xp = int(total_recent_xp / 7) if recent else 100
                else:
                    daily_xp = 100  # Default
            else:
                daily_xp = 100  # Default
        
        # Calculate progression
        total_xp_earned = daily_xp * days
        projected_xp = current_xp + total_xp_earned
        projected_level = self.calculate_level(projected_xp)
        
        # Calculate days to next level
        xp_to_next = self.xp_to_next_level(current_level, current_xp)
        days_to_next = (xp_to_next / daily_xp) if daily_xp > 0 else 0
        
        # Calculate days to milestone
        next_milestone = self._get_next_milestone(current_level)
        days_to_milestone = None
        if next_milestone:
            xp_to_milestone = self.xp_for_level(next_milestone) - current_xp
            days_to_milestone = (xp_to_milestone / daily_xp) if daily_xp > 0 else None
        
        # Daily progression breakdown
        daily_breakdown = []
        cumulative_xp = current_xp
        cumulative_level = current_level
        for day in range(1, days + 1):
            cumulative_xp += daily_xp
            new_level = self.calculate_level(cumulative_xp)
            leveled_up = new_level > cumulative_level
            cumulative_level = new_level
            
            daily_breakdown.append({
                'day': day,
                'xp_earned': daily_xp,
                'cumulative_xp': cumulative_xp,
                'level': cumulative_level,
                'leveled_up': leveled_up
            })
        
        return {
            'success': True,
            'user_id': user_id,
            'current_level': current_level,
            'current_xp': current_xp,
            'projected_level': projected_level,
            'projected_xp': projected_xp,
            'daily_xp_estimate': daily_xp,
            'days_analyzed': days,
            'total_xp_earned': total_xp_earned,
            'levels_gained': projected_level - current_level,
            'days_to_next_level': round(days_to_next, 1),
            'days_to_milestone': round(days_to_milestone, 1) if days_to_milestone else None,
            'next_milestone': next_milestone,
            'daily_breakdown': daily_breakdown
        }
    
    def calculate_rewards(self, level: int, include_future: bool = False, 
                         future_levels: int = 10) -> Dict[str, Any]:
        """
        Calculate rewards for a level or range of levels
        """
        # Current level rewards
        current_rewards = self.level_rewards.get(level, {})
        
        # Calculate total rewards if include_future
        future_rewards = []
        if include_future:
            for future_level in range(level + 1, level + future_levels + 1):
                future_reward = self.level_rewards.get(future_level, {})
                future_rewards.append({
                    'level': future_level,
                    'rewards': future_reward
                })
        
        # Calculate cumulative rewards
        cumulative = {
            'total_stat_points': 0,
            'total_unlock_points': 0,
            'total_xp_bonus': 0,
            'themes_unlocked': set(),
            'templates_unlocked': set(),
            'titles_unlocked': []
        }
        
        for lvl in range(1, level + 1):
            lvl_rewards = self.level_rewards.get(lvl, {})
            cumulative['total_stat_points'] += lvl_rewards.get('stat_points', 0)
            cumulative['total_unlock_points'] += lvl_rewards.get('unlock_points', 0)
            cumulative['total_xp_bonus'] = max(cumulative['total_xp_bonus'], 
                                              lvl_rewards.get('xp_bonus_percent', 0))
            cumulative['themes_unlocked'].update(lvl_rewards.get('theme_unlocks', []))
            cumulative['templates_unlocked'].update(lvl_rewards.get('template_unlocks', []))
            if lvl_rewards.get('title_unlock'):
                cumulative['titles_unlocked'].append({
                    'level': lvl,
                    'title': lvl_rewards.get('title_unlock')
                })
        
        return {
            'success': True,
            'level': level,
            'current_rewards': current_rewards,
            'cumulative_rewards': {
                'total_stat_points': cumulative['total_stat_points'],
                'total_unlock_points': cumulative['total_unlock_points'],
                'max_xp_bonus_percent': cumulative['total_xp_bonus'],
                'themes_unlocked': list(cumulative['themes_unlocked']),
                'templates_unlocked': list(cumulative['templates_unlocked']),
                'titles_unlocked': cumulative['titles_unlocked']
            },
            'future_rewards': future_rewards if include_future else None,
            'next_milestone': self._get_next_milestone(level),
            'milestone_rewards': self.level_rewards.get(self._get_next_milestone(level) or level, {})
        }
    
    def calculate_optimal_activity_plan(self, user_id: str, target_level: int,
                                       available_activities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate optimal activity plan to reach target level
        """
        user_stats = self.get_user_stats(user_id)
        current_level = user_stats.get('level', 1)
        current_xp = user_stats.get('total_xp', 0)
        
        if target_level <= current_level:
            return {
                'success': False,
                'error': 'Target level must be higher than current level'
            }
        
        xp_needed = self.xp_for_level(target_level) - current_xp
        
        # Analyze activities
        activity_analysis = []
        for activity in available_activities:
            activity_name = activity.get('name', 'Unknown')
            xp_per_activity = activity.get('xp_reward', 0)
            time_per_activity = activity.get('time_minutes', 0)
            energy_cost = activity.get('energy_cost', 0)
            
            if xp_per_activity > 0:
                activities_needed = (xp_needed / xp_per_activity)
                total_time = activities_needed * time_per_activity
                total_energy = activities_needed * energy_cost
                efficiency = xp_per_activity / max(1, time_per_activity)  # XP per minute
                
                activity_analysis.append({
                    'name': activity_name,
                    'xp_per_activity': xp_per_activity,
                    'activities_needed': round(activities_needed, 1),
                    'total_time_minutes': round(total_time, 1),
                    'total_energy': round(total_energy, 1),
                    'efficiency': round(efficiency, 2),
                    'recommended': False
                })
        
        # Sort by efficiency
        activity_analysis.sort(key=lambda x: x['efficiency'], reverse=True)
        
        # Mark top 3 as recommended
        for i, activity in enumerate(activity_analysis[:3]):
            activity['recommended'] = True
        
        # Calculate optimal plan
        if activity_analysis:
            best_activity = activity_analysis[0]
            optimal_plan = {
                'recommended_activity': best_activity['name'],
                'activities_needed': int(best_activity['activities_needed']),
                'estimated_time_hours': round(best_activity['total_time_minutes'] / 60, 1),
                'estimated_energy': int(best_activity['total_energy']),
                'efficiency': best_activity['efficiency']
            }
        else:
            optimal_plan = None
        
        return {
            'success': True,
            'user_id': user_id,
            'current_level': current_level,
            'target_level': target_level,
            'xp_needed': xp_needed,
            'activity_analysis': activity_analysis,
            'optimal_plan': optimal_plan
        }
    
    def prestige(self, user_id: str) -> Dict[str, Any]:
        """
        Prestige: Reset to level 1 with permanent bonuses
        
        Returns:
            Dict with prestige info and bonuses
        """
        if user_id not in self.player_data:
            return {'success': False, 'error': 'Player not found'}
        
        player = self.player_data[user_id]
        
        if player['current_level'] < 100:
            return {
                'success': False,
                'error': 'Must be level 100+ to prestige'
            }
        
        # Calculate prestige bonus
        prestige_level = player.get('prestige_level', 0) + 1
        xp_bonus_percent = prestige_level * 10  # +10% per prestige
        
        # Reset level but keep some progress
        old_level = player['current_level']
        old_xp = player['total_xp']
        
        # Reset to level 1
        player['current_level'] = 1
        player['current_xp'] = 0
        player['total_xp'] = 0
        player['xp_to_next_level'] = 1000
        player['level_progress'] = 0.0
        player['title'] = 'Novice Hunter'
        player['prestige_level'] = prestige_level
        player['prestige_xp_bonus'] = xp_bonus_percent
        
        # Keep unlocked content
        # Stats reset but can be reallocated faster
        
        # Enhanced prestige rewards
        prestige_rewards = {
            'prestige_points': prestige_level * 100,
            'unlock_points': prestige_level * 50,
            'stat_points': prestige_level * 10,
            'skill_points': prestige_level * 5,
            'special_title': f'Prestige {prestige_level} Hunter'
        }
        
        # Add prestige rewards to player
        if 'prestige_rewards' not in player:
            player['prestige_rewards'] = []
        player['prestige_rewards'].append({
            'prestige_level': prestige_level,
            'rewards': prestige_rewards,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {
            'success': True,
            'prestige_level': prestige_level,
            'xp_bonus_percent': xp_bonus_percent,
            'old_level': old_level,
            'old_xp': old_xp,
            'rewards': prestige_rewards,
            'message': f'Prestiged! You now have +{xp_bonus_percent}% XP bonus permanently and received prestige rewards!'
        }
    
    def unlock_skill(self, user_id: str, tree_name: str, skill_id: str, level: int = 1) -> Dict[str, Any]:
        """Unlock or upgrade a skill in a skill tree"""
        if user_id not in self.player_data:
            return {'success': False, 'error': 'Player not found'}
        
        if tree_name not in self.skill_trees:
            return {'success': False, 'error': f'Invalid skill tree: {tree_name}'}
        
        tree = self.skill_trees[tree_name]
        if skill_id not in tree['skills']:
            return {'success': False, 'error': f'Invalid skill: {skill_id}'}
        
        skill = tree['skills'][skill_id]
        player = self.player_data[user_id]
        
        # Initialize skill data if needed
        if 'skills' not in player:
            player['skills'] = {}
        if tree_name not in player['skills']:
            player['skills'][tree_name] = {}
        if skill_id not in player['skills'][tree_name]:
            player['skills'][tree_name][skill_id] = {'level': 0, 'unlocked': False}
        
        skill_data = player['skills'][tree_name][skill_id]
        current_level = skill_data.get('level', 0)
        
        # Check prerequisites
        for prereq in skill.get('prerequisites', []):
            prereq_tree, prereq_skill = prereq.split('.') if '.' in prereq else (tree_name, prereq)
            if prereq_tree not in player.get('skills', {}) or prereq_skill not in player['skills'].get(prereq_tree, {}):
                return {'success': False, 'error': f'Prerequisite skill {prereq} not unlocked'}
            if not player['skills'][prereq_tree][prereq_skill].get('unlocked', False):
                return {'success': False, 'error': f'Prerequisite skill {prereq} not unlocked'}
        
        # Check if can upgrade
        if current_level >= skill['max_level']:
            return {'success': False, 'error': f'Skill already at max level ({skill["max_level"]})'}
        
        # Check cost
        cost = skill['cost_per_level'] * (current_level + 1)
        available_points = player.get('skill_points', 0)
        if available_points < cost:
            return {'success': False, 'error': f'Not enough skill points. Need {cost}, have {available_points}'}
        
        # Unlock/upgrade skill
        skill_data['level'] = current_level + 1
        skill_data['unlocked'] = True
        player['skill_points'] = available_points - cost
        
        # Calculate bonuses
        bonuses = {}
        for bonus_type, bonus_value in skill.get('bonus_per_level', {}).items():
            bonuses[bonus_type] = bonus_value * skill_data['level']
        
        return {
            'success': True,
            'tree_name': tree_name,
            'skill_id': skill_id,
            'skill_name': skill['name'],
            'new_level': skill_data['level'],
            'max_level': skill['max_level'],
            'cost_paid': cost,
            'remaining_skill_points': player['skill_points'],
            'bonuses': bonuses
        }
    
    def get_skill_tree_progress(self, user_id: str) -> Dict[str, Any]:
        """Get skill tree progress for a user"""
        if user_id not in self.player_data:
            return {'success': False, 'error': 'Player not found'}
        
        player = self.player_data[user_id]
        player_skills = player.get('skills', {})
        
        skill_progress = {}
        for tree_name, tree in self.skill_trees.items():
            tree_progress = {
                'name': tree['name'],
                'skills': {},
                'total_skills': len(tree['skills']),
                'unlocked_skills': 0,
                'total_levels': 0,
                'max_levels': 0
            }
            
            for skill_id, skill in tree['skills'].items():
                skill_data = player_skills.get(tree_name, {}).get(skill_id, {'level': 0, 'unlocked': False})
                level = skill_data.get('level', 0)
                unlocked = skill_data.get('unlocked', False)
                
                tree_progress['skills'][skill_id] = {
                    'name': skill['name'],
                    'description': skill['description'],
                    'level': level,
                    'max_level': skill['max_level'],
                    'unlocked': unlocked,
                    'cost_per_level': skill['cost_per_level'],
                    'prerequisites': skill.get('prerequisites', [])
                }
                
                if unlocked:
                    tree_progress['unlocked_skills'] += 1
                tree_progress['total_levels'] += level
                tree_progress['max_levels'] += skill['max_level']
            
            skill_progress[tree_name] = tree_progress
        
        return {
            'success': True,
            'user_id': user_id,
            'skill_points': player.get('skill_points', 0),
            'skill_trees': skill_progress
        }


# Global instance
hunters_leveling_system = LevelingSystem()

