"""
Game Achievements and Milestones System
Awards statistics points for completing achievements and reaching milestones
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict


class Achievement:
    """Represents a single achievement"""
    
    def __init__(self, achievement_id: str, name: str, description: str, 
                 points: int, category: str = 'general', icon: str = '🏆'):
        self.id = achievement_id
        self.name = name
        self.description = description
        self.points = points  # Statistics points awarded
        self.category = category  # underholdning, porn, rettigheder, general
        self.icon = icon
        self.earned_at = None
        self.progress = 0
        self.target = 1
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'points': self.points,
            'category': self.category,
            'icon': self.icon,
            'earned': self.earned_at is not None,
            'earned_at': self.earned_at.isoformat() if self.earned_at else None,
            'progress': self.progress,
            'target': self.target,
            'progress_percent': min(100, int((self.progress / self.target) * 100)) if self.target > 0 else 0
        }


class Milestone:
    """Represents a milestone"""
    
    def __init__(self, milestone_id: str, name: str, description: str,
                 target_value: int, points: int, category: str = 'general', icon: str = '🎯'):
        self.id = milestone_id
        self.name = name
        self.description = description
        self.target_value = target_value
        self.points = points  # Statistics points awarded
        self.category = category
        self.icon = icon
        self.reached_at = None
        self.current_value = 0
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'target_value': self.target_value,
            'points': self.points,
            'category': self.category,
            'icon': self.icon,
            'reached': self.current_value >= self.target_value,
            'reached_at': self.reached_at.isoformat() if self.reached_at else None,
            'current_value': self.current_value,
            'progress_percent': min(100, int((self.current_value / self.target_value) * 100)) if self.target_value > 0 else 0
        }


class GameAchievementSystem:
    """Manages achievements and milestones for the game"""
    
    def __init__(self):
        """Initialize achievement system with all achievements and milestones"""
        self.achievements = self._initialize_achievements()
        self.milestones = self._initialize_milestones()
        self.user_achievements = {}  # {user_id: {achievement_id: Achievement}}
        self.user_milestones = {}  # {user_id: {milestone_id: Milestone}}
        self.user_stats_points = {}  # {user_id: total_stats_points}
        self.achievement_categories = self._initialize_categories()
        self.achievement_tiers = self._initialize_tiers()
    
    def _initialize_achievements(self) -> Dict[str, Achievement]:
        """Initialize all available achievements"""
        achievements = {}
        
        # General achievements
        achievements['first_video'] = Achievement(
            'first_video',
            'Første Video',
            'Opret dit første dokumentar',
            points=100,
            category='general',
            icon='🎬'
        )
        
        achievements['video_master'] = Achievement(
            'video_master',
            'Video Mester',
            'Opret 10 dokumentarer',
            points=500,
            category='general',
            icon='🎥'
        )
        
        achievements['perfectionist'] = Achievement(
            'perfectionist',
            'Perfektionist',
            'Opret en video med 100% kvalitet',
            points=300,
            category='general',
            icon='⭐'
        )
        
        # Category-specific achievements - Underholdning
        achievements['entertainment_starter'] = Achievement(
            'entertainment_starter',
            'Underholdnings Starter',
            'Opret dit første underholdningsvideo',
            points=150,
            category='underholdning',
            icon='🎭'
        )
        
        achievements['entertainment_master'] = Achievement(
            'entertainment_master',
            'Underholdnings Mester',
            'Opret 5 underholdningsvideoer',
            points=600,
            category='underholdning',
            icon='🎪'
        )
        
        # Category-specific achievements - Porn
        achievements['adult_starter'] = Achievement(
            'adult_starter',
            'Voksen Starter',
            'Opret dit første voksenindhold',
            points=150,
            category='porn',
            icon='🔞'
        )
        
        achievements['adult_master'] = Achievement(
            'adult_master',
            'Voksen Mester',
            'Opret 5 voksenindholds videoer',
            points=600,
            category='porn',
            icon='💋'
        )
        
        # Category-specific achievements - Rettigheder
        achievements['rights_starter'] = Achievement(
            'rights_starter',
            'Rettigheder Starter',
            'Opret dit første rettighedsvideo',
            points=150,
            category='rettigheder',
            icon='⚖️'
        )
        
        achievements['rights_master'] = Achievement(
            'rights_master',
            'Rettigheder Mester',
            'Opret 5 rettighedsvideoer',
            points=600,
            category='rettigheder',
            icon='📜'
        )
        
        # Special achievements
        achievements['speed_demon'] = Achievement(
            'speed_demon',
            'Hastigheds Dæmon',
            'Opret 5 videoer på én dag',
            points=800,
            category='general',
            icon='⚡'
        )
        
        achievements['quality_seeker'] = Achievement(
            'quality_seeker',
            'Kvalitets Søger',
            'Opret 10 videoer med kvalitet over 80%',
            points=700,
            category='general',
            icon='💎'
        )
        
        # Battle achievements
        achievements['first_battle'] = Achievement(
            'first_battle',
            'Første Kamp',
            'Deltag i din første fantasy kamp',
            points=200,
            category='battle',
            icon='⚔️'
        )
        
        achievements['battle_warrior'] = Achievement(
            'battle_warrior',
            'Kamp Kriger',
            'Vind 10 fantasy kampe',
            points=500,
            category='battle',
            icon='🗡️'
        )
        
        achievements['tournament_champion'] = Achievement(
            'tournament_champion',
            'Turneringsmester',
            'Vind en fantasy turnering',
            points=1000,
            category='battle',
            icon='👑'
        )
        
        achievements['realm_conqueror'] = Achievement(
            'realm_conqueror',
            'Rigsforsvinder',
            'Vind kampe i alle 4 fantasy riger',
            points=800,
            category='battle',
            icon='🏰'
        )
        
        achievements['undefeated'] = Achievement(
            'undefeated',
            'Uovervindelig',
            'Vind 5 kampe i træk',
            points=600,
            category='battle',
            icon='🛡️'
        )
        
        achievements['battle_master'] = Achievement(
            'battle_master',
            'Kampmester',
            'Vind 50 fantasy kampe',
            points=1500,
            category='battle',
            icon='⚡'
        )
        
        return achievements
    
    def _initialize_categories(self) -> Dict[str, Dict]:
        """Initialize achievement categories with metadata"""
        return {
            'general': {
                'name': 'General',
                'description': 'General achievements for all activities',
                'icon': '⭐',
                'color': '#00ff88'
            },
            'battle': {
                'name': 'Battle',
                'description': 'Battle and combat achievements',
                'icon': '⚔️',
                'color': '#ff4444'
            },
            'underholdning': {
                'name': 'Entertainment',
                'description': 'Entertainment content achievements',
                'icon': '🎭',
                'color': '#ffaa00'
            },
            'porn': {
                'name': 'Adult Content',
                'description': 'Adult content achievements',
                'icon': '🔞',
                'color': '#ff00ff'
            },
            'rettigheder': {
                'name': 'Rights',
                'description': 'Rights and legal content achievements',
                'icon': '⚖️',
                'color': '#00aaff'
            },
            'agent': {
                'name': 'Agent',
                'description': 'Agent system achievements',
                'icon': '🤖',
                'color': '#00ff88'
            },
            'tech': {
                'name': 'Technology',
                'description': 'Tech tree and research achievements',
                'icon': '🔬',
                'color': '#00aaff'
            },
            'hunter': {
                'name': 'Hunter',
                'description': 'Hunter game achievements',
                'icon': '🎯',
                'color': '#ffaa00'
            }
        }
    
    def _initialize_tiers(self) -> Dict[str, Dict]:
        """Initialize achievement tiers with rewards"""
        return {
            'bronze': {
                'name': 'Bronze',
                'multiplier': 1.0,
                'bonus_points': 0,
                'color': '#cd7f32',
                'icon': '🥉'
            },
            'silver': {
                'name': 'Silver',
                'multiplier': 1.2,
                'bonus_points': 50,
                'color': '#c0c0c0',
                'icon': '🥈'
            },
            'gold': {
                'name': 'Gold',
                'multiplier': 1.5,
                'bonus_points': 100,
                'color': '#ffd700',
                'icon': '🥇'
            },
            'platinum': {
                'name': 'Platinum',
                'multiplier': 2.0,
                'bonus_points': 250,
                'color': '#e5e4e2',
                'icon': '💎'
            },
            'legendary': {
                'name': 'Legendary',
                'multiplier': 3.0,
                'bonus_points': 500,
                'color': '#ff00ff',
                'icon': '👑'
            }
        }
    
    def get_achievements_by_category(self, user_id: str) -> Dict[str, Any]:
        """Get achievements grouped by category"""
        if user_id not in self.user_achievements:
            return {'success': False, 'error': 'User not found'}
        
        user_achs = self.user_achievements[user_id]
        categorized = {cat: [] for cat in self.achievement_categories.keys()}
        categorized['all'] = []
        
        for ach_id, achievement in user_achs.items():
            if ach_id in self.achievements:
                ach_data = achievement.to_dict()
                category = achievement.category or 'general'
                categorized[category].append(ach_data)
                categorized['all'].append(ach_data)
        
        # Add category metadata
        result = {
            'success': True,
            'user_id': user_id,
            'categories': {}
        }
        
        for cat_id, cat_info in self.achievement_categories.items():
            earned = len([a for a in categorized[cat_id] if a.get('earned', False)])
            total = len(categorized[cat_id])
            
            result['categories'][cat_id] = {
                'name': cat_info['name'],
                'description': cat_info['description'],
                'icon': cat_info['icon'],
                'color': cat_info['color'],
                'achievements': categorized[cat_id],
                'earned': earned,
                'total': total,
                'completion_percent': (earned / total * 100) if total > 0 else 0
            }
        
        return result
    
    def get_achievement_rewards(self, achievement_id: str) -> Dict[str, Any]:
        """Get rewards for a specific achievement"""
        if achievement_id not in self.achievements:
            return {'success': False, 'error': 'Achievement not found'}
        
        achievement = self.achievements[achievement_id]
        base_points = achievement.points
        
        # Determine tier based on points
        if base_points >= 1000:
            tier = 'legendary'
        elif base_points >= 500:
            tier = 'platinum'
        elif base_points >= 300:
            tier = 'gold'
        elif base_points >= 150:
            tier = 'silver'
        else:
            tier = 'bronze'
        
        tier_info = self.achievement_tiers[tier]
        final_points = int(base_points * tier_info['multiplier']) + tier_info['bonus_points']
        
        return {
            'success': True,
            'achievement_id': achievement_id,
            'base_points': base_points,
            'tier': tier,
            'tier_info': tier_info,
            'final_points': final_points,
            'bonus_points': tier_info['bonus_points'],
            'multiplier': tier_info['multiplier']
        }
    
    def _initialize_milestones(self) -> Dict[str, Milestone]:
        """Initialize all available milestones"""
        milestones = {}
        
        # General milestones
        milestones['videos_5'] = Milestone(
            'videos_5',
            '5 Videoer',
            'Opret 5 dokumentarer',
            target_value=5,
            points=200,
            category='general',
            icon='🎯'
        )
        
        milestones['videos_10'] = Milestone(
            'videos_10',
            '10 Videoer',
            'Opret 10 dokumentarer',
            target_value=10,
            points=400,
            category='general',
            icon='🎯'
        )
        
        milestones['videos_25'] = Milestone(
            'videos_25',
            '25 Videoer',
            'Opret 25 dokumentarer',
            target_value=25,
            points=1000,
            category='general',
            icon='🎯'
        )
        
        milestones['videos_50'] = Milestone(
            'videos_50',
            '50 Videoer',
            'Opret 50 dokumentarer',
            target_value=50,
            points=2500,
            category='general',
            icon='🎯'
        )
        
        milestones['videos_100'] = Milestone(
            'videos_100',
            '100 Videoer',
            'Opret 100 dokumentarer',
            target_value=100,
            points=5000,
            category='general',
            icon='🏆'
        )
        
        # Category milestones - Underholdning
        milestones['entertainment_10'] = Milestone(
            'entertainment_10',
            '10 Underholdningsvideoer',
            'Opret 10 underholdningsvideoer',
            target_value=10,
            points=800,
            category='underholdning',
            icon='🎭'
        )
        
        milestones['entertainment_25'] = Milestone(
            'entertainment_25',
            '25 Underholdningsvideoer',
            'Opret 25 underholdningsvideoer',
            target_value=25,
            points=2000,
            category='underholdning',
            icon='🎪'
        )
        
        # Category milestones - Porn
        milestones['porn_10'] = Milestone(
            'porn_10',
            '10 Voksenindholds Videoer',
            'Opret 10 voksenindholds videoer',
            target_value=10,
            points=800,
            category='porn',
            icon='🔞'
        )
        
        milestones['porn_25'] = Milestone(
            'porn_25',
            '25 Voksenindholds Videoer',
            'Opret 25 voksenindholds videoer',
            target_value=25,
            points=2000,
            category='porn',
            icon='💋'
        )
        
        # Category milestones - Rettigheder
        milestones['rights_10'] = Milestone(
            'rights_10',
            '10 Rettighedsvideoer',
            'Opret 10 rettighedsvideoer',
            target_value=10,
            points=800,
            category='rettigheder',
            icon='⚖️'
        )
        
        milestones['rights_25'] = Milestone(
            'rights_25',
            '25 Rettighedsvideoer',
            'Opret 25 rettighedsvideoer',
            target_value=25,
            points=2000,
            category='rettigheder',
            icon='📜'
        )
        
        # Quality milestones
        milestones['avg_quality_80'] = Milestone(
            'avg_quality_80',
            'Gennemsnitlig Kvalitet 80%',
            'Opnå gennemsnitlig kvalitet på 80%',
            target_value=80,
            points=600,
            category='general',
            icon='⭐'
        )
        
        milestones['avg_quality_90'] = Milestone(
            'avg_quality_90',
            'Gennemsnitlig Kvalitet 90%',
            'Opnå gennemsnitlig kvalitet på 90%',
            target_value=90,
            points=1200,
            category='general',
            icon='💎'
        )
        
        # Battle milestones
        milestones['battles_10'] = Milestone(
            'battles_10',
            '10 Kampe',
            'Deltag i 10 fantasy kampe',
            target_value=10,
            points=400,
            category='battle',
            icon='⚔️'
        )
        
        milestones['battles_25'] = Milestone(
            'battles_25',
            '25 Kampe',
            'Deltag i 25 fantasy kampe',
            target_value=25,
            points=800,
            category='battle',
            icon='🗡️'
        )
        
        milestones['battles_50'] = Milestone(
            'battles_50',
            '50 Kampe',
            'Deltag i 50 fantasy kampe',
            target_value=50,
            points=1500,
            category='battle',
            icon='⚡'
        )
        
        milestones['battles_100'] = Milestone(
            'battles_100',
            '100 Kampe',
            'Deltag i 100 fantasy kampe',
            target_value=100,
            points=3000,
            category='battle',
            icon='🏆'
        )
        
        milestones['wins_10'] = Milestone(
            'wins_10',
            '10 Sejre',
            'Vind 10 fantasy kampe',
            target_value=10,
            points=500,
            category='battle',
            icon='👑'
        )
        
        milestones['wins_25'] = Milestone(
            'wins_25',
            '25 Sejre',
            'Vind 25 fantasy kampe',
            target_value=25,
            points=1200,
            category='battle',
            icon='🎖️'
        )
        
        milestones['tournaments_5'] = Milestone(
            'tournaments_5',
            '5 Turneringer',
            'Deltag i 5 fantasy turneringer',
            target_value=5,
            points=1000,
            category='battle',
            icon='🏟️'
        )
        
        return milestones
    
    def get_user_achievements(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all achievements for a user with progress"""
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = {}
            # Initialize with all achievements
            for ach_id, achievement in self.achievements.items():
                self.user_achievements[user_id][ach_id] = Achievement(
                    achievement.id, achievement.name, achievement.description,
                    achievement.points, achievement.category, achievement.icon
                )
        
        return [ach.to_dict() for ach in self.user_achievements[user_id].values()]
    
    def get_user_milestones(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all milestones for a user with progress"""
        if user_id not in self.user_milestones:
            self.user_milestones[user_id] = {}
            # Initialize with all milestones
            for mil_id, milestone in self.milestones.items():
                self.user_milestones[user_id][mil_id] = Milestone(
                    milestone.id, milestone.name, milestone.description,
                    milestone.target_value, milestone.points, milestone.category, milestone.icon
                )
        
        return [mil.to_dict() for mil in self.user_milestones[user_id].values()]
    
    def check_and_award_achievements(self, user_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check achievements based on user stats and award points
        Returns list of newly earned achievements
        """
        newly_earned = []
        
        if user_id not in self.user_achievements:
            self.user_achievements[user_id] = {}
        
        if user_id not in self.user_stats_points:
            self.user_stats_points[user_id] = 0
        
        # Initialize achievements if needed
        for ach_id, achievement in self.achievements.items():
            if ach_id not in self.user_achievements[user_id]:
                self.user_achievements[user_id][ach_id] = Achievement(
                    achievement.id, achievement.name, achievement.description,
                    achievement.points, achievement.category, achievement.icon
                )
        
        user_achs = self.user_achievements[user_id]
        
        # Check general achievements
        total_videos = stats.get('total_videos', 0)
        high_quality_count = stats.get('high_quality_videos', 0)
        videos_today = stats.get('videos_today', 0)
        
        # First video
        if total_videos >= 1 and not user_achs['first_video'].earned_at:
            user_achs['first_video'].earned_at = datetime.utcnow()
            user_achs['first_video'].progress = 1
            self.user_stats_points[user_id] += user_achs['first_video'].points
            newly_earned.append(user_achs['first_video'].to_dict())
        
        # 10 videos
        if total_videos >= 10 and not user_achs['video_master'].earned_at:
            user_achs['video_master'].earned_at = datetime.utcnow()
            user_achs['video_master'].progress = 10
            self.user_stats_points[user_id] += user_achs['video_master'].points
            newly_earned.append(user_achs['video_master'].to_dict())
        
        # Perfect quality
        has_perfect = stats.get('has_perfect_quality', False)
        if has_perfect and not user_achs['perfectionist'].earned_at:
            user_achs['perfectionist'].earned_at = datetime.utcnow()
            user_achs['perfectionist'].progress = 1
            self.user_stats_points[user_id] += user_achs['perfectionist'].points
            newly_earned.append(user_achs['perfectionist'].to_dict())
        
        # Speed demon
        if videos_today >= 5 and not user_achs['speed_demon'].earned_at:
            user_achs['speed_demon'].earned_at = datetime.utcnow()
            user_achs['speed_demon'].progress = videos_today
            self.user_stats_points[user_id] += user_achs['speed_demon'].points
            newly_earned.append(user_achs['speed_demon'].to_dict())
        
        # Quality seeker
        if high_quality_count >= 10 and not user_achs['quality_seeker'].earned_at:
            user_achs['quality_seeker'].earned_at = datetime.utcnow()
            user_achs['quality_seeker'].progress = high_quality_count
            self.user_stats_points[user_id] += user_achs['quality_seeker'].points
            newly_earned.append(user_achs['quality_seeker'].to_dict())
        
        # Battle achievements
        battles_won = stats.get('battles_won', 0)
        battles_total = stats.get('battles_total', 0)
        fantasy_battles = stats.get('fantasy_battles', 0)
        tournaments_won = stats.get('tournaments_won', 0)
        win_streak = stats.get('battle_win_streak', 0)
        realms_conquered = stats.get('realms_conquered', set())
        
        # First battle
        if fantasy_battles >= 1 and not user_achs['first_battle'].earned_at:
            user_achs['first_battle'].earned_at = datetime.utcnow()
            user_achs['first_battle'].progress = 1
            self.user_stats_points[user_id] += user_achs['first_battle'].points
            newly_earned.append(user_achs['first_battle'].to_dict())
        
        # Battle warrior (10 wins)
        if battles_won >= 10 and not user_achs['battle_warrior'].earned_at:
            user_achs['battle_warrior'].earned_at = datetime.utcnow()
            user_achs['battle_warrior'].progress = battles_won
            self.user_stats_points[user_id] += user_achs['battle_warrior'].points
            newly_earned.append(user_achs['battle_warrior'].to_dict())
        
        # Tournament champion
        if tournaments_won >= 1 and not user_achs['tournament_champion'].earned_at:
            user_achs['tournament_champion'].earned_at = datetime.utcnow()
            user_achs['tournament_champion'].progress = tournaments_won
            self.user_stats_points[user_id] += user_achs['tournament_champion'].points
            newly_earned.append(user_achs['tournament_champion'].to_dict())
        
        # Realm conqueror (all 4 realms)
        if isinstance(realms_conquered, set) and len(realms_conquered) >= 4:
            if not user_achs['realm_conqueror'].earned_at:
                user_achs['realm_conqueror'].earned_at = datetime.utcnow()
                user_achs['realm_conqueror'].progress = len(realms_conquered)
                self.user_stats_points[user_id] += user_achs['realm_conqueror'].points
                newly_earned.append(user_achs['realm_conqueror'].to_dict())
        elif isinstance(realms_conquered, dict):
            conquered_count = sum(1 for v in realms_conquered.values() if v)
            if conquered_count >= 4 and not user_achs['realm_conqueror'].earned_at:
                user_achs['realm_conqueror'].earned_at = datetime.utcnow()
                user_achs['realm_conqueror'].progress = conquered_count
                self.user_stats_points[user_id] += user_achs['realm_conqueror'].points
                newly_earned.append(user_achs['realm_conqueror'].to_dict())
        
        # Undefeated (5 win streak)
        if win_streak >= 5 and not user_achs['undefeated'].earned_at:
            user_achs['undefeated'].earned_at = datetime.utcnow()
            user_achs['undefeated'].progress = win_streak
            self.user_stats_points[user_id] += user_achs['undefeated'].points
            newly_earned.append(user_achs['undefeated'].to_dict())
        
        # Battle master (50 wins)
        if battles_won >= 50 and not user_achs['battle_master'].earned_at:
            user_achs['battle_master'].earned_at = datetime.utcnow()
            user_achs['battle_master'].progress = battles_won
            self.user_stats_points[user_id] += user_achs['battle_master'].points
            newly_earned.append(user_achs['battle_master'].to_dict())
        
        # Category-specific achievements
        category_videos = stats.get('category_videos', {})
        
        # Underholdning
        ent_count = category_videos.get('underholdning', 0)
        if ent_count >= 1 and not user_achs['entertainment_starter'].earned_at:
            user_achs['entertainment_starter'].earned_at = datetime.utcnow()
            user_achs['entertainment_starter'].progress = ent_count
            self.user_stats_points[user_id] += user_achs['entertainment_starter'].points
            newly_earned.append(user_achs['entertainment_starter'].to_dict())
        
        if ent_count >= 5 and not user_achs['entertainment_master'].earned_at:
            user_achs['entertainment_master'].earned_at = datetime.utcnow()
            user_achs['entertainment_master'].progress = ent_count
            self.user_stats_points[user_id] += user_achs['entertainment_master'].points
            newly_earned.append(user_achs['entertainment_master'].to_dict())
        
        # Porn
        porn_count = category_videos.get('porn', 0)
        if porn_count >= 1 and not user_achs['adult_starter'].earned_at:
            user_achs['adult_starter'].earned_at = datetime.utcnow()
            user_achs['adult_starter'].progress = porn_count
            self.user_stats_points[user_id] += user_achs['adult_starter'].points
            newly_earned.append(user_achs['adult_starter'].to_dict())
        
        if porn_count >= 5 and not user_achs['adult_master'].earned_at:
            user_achs['adult_master'].earned_at = datetime.utcnow()
            user_achs['adult_master'].progress = porn_count
            self.user_stats_points[user_id] += user_achs['adult_master'].points
            newly_earned.append(user_achs['adult_master'].to_dict())
        
        # Rettigheder
        rights_count = category_videos.get('rettigheder', 0)
        if rights_count >= 1 and not user_achs['rights_starter'].earned_at:
            user_achs['rights_starter'].earned_at = datetime.utcnow()
            user_achs['rights_starter'].progress = rights_count
            self.user_stats_points[user_id] += user_achs['rights_starter'].points
            newly_earned.append(user_achs['rights_starter'].to_dict())
        
        if rights_count >= 5 and not user_achs['rights_master'].earned_at:
            user_achs['rights_master'].earned_at = datetime.utcnow()
            user_achs['rights_master'].progress = rights_count
            self.user_stats_points[user_id] += user_achs['rights_master'].points
            newly_earned.append(user_achs['rights_master'].to_dict())
        
        return newly_earned
    
    def check_and_award_milestones(self, user_id: str, stats: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Check milestones based on user stats and award points
        Returns list of newly reached milestones
        """
        newly_reached = []
        
        if user_id not in self.user_milestones:
            self.user_milestones[user_id] = {}
        
        if user_id not in self.user_stats_points:
            self.user_stats_points[user_id] = 0
        
        # Initialize milestones if needed
        for mil_id, milestone in self.milestones.items():
            if mil_id not in self.user_milestones[user_id]:
                self.user_milestones[user_id][mil_id] = Milestone(
                    milestone.id, milestone.name, milestone.description,
                    milestone.target_value, milestone.points, milestone.category, milestone.icon
                )
        
        user_mils = self.user_milestones[user_id]
        total_videos = stats.get('total_videos', 0)
        category_videos = stats.get('category_videos', {})
        avg_quality = stats.get('avg_quality', 0) * 100  # Convert to percentage
        
        # Battle stats
        battles_total = stats.get('battles_total', 0)
        battles_won = stats.get('battles_won', 0)
        tournaments_joined = stats.get('tournaments_joined', 0)
        
        # Video count milestones
        video_milestones = ['videos_5', 'videos_10', 'videos_25', 'videos_50', 'videos_100']
        for mil_id in video_milestones:
            mil = user_mils[mil_id]
            mil.current_value = total_videos
            if total_videos >= mil.target_value and not mil.reached_at:
                mil.reached_at = datetime.utcnow()
                self.user_stats_points[user_id] += mil.points
                newly_reached.append(mil.to_dict())
        
        # Category milestones - Underholdning
        ent_count = category_videos.get('underholdning', 0)
        ent_mils = ['entertainment_10', 'entertainment_25']
        for mil_id in ent_mils:
            mil = user_mils[mil_id]
            mil.current_value = ent_count
            if ent_count >= mil.target_value and not mil.reached_at:
                mil.reached_at = datetime.utcnow()
                self.user_stats_points[user_id] += mil.points
                newly_reached.append(mil.to_dict())
        
        # Category milestones - Porn
        porn_count = category_videos.get('porn', 0)
        porn_mils = ['porn_10', 'porn_25']
        for mil_id in porn_mils:
            mil = user_mils[mil_id]
            mil.current_value = porn_count
            if porn_count >= mil.target_value and not mil.reached_at:
                mil.reached_at = datetime.utcnow()
                self.user_stats_points[user_id] += mil.points
                newly_reached.append(mil.to_dict())
        
        # Category milestones - Rettigheder
        rights_count = category_videos.get('rettigheder', 0)
        rights_mils = ['rights_10', 'rights_25']
        for mil_id in rights_mils:
            mil = user_mils[mil_id]
            mil.current_value = rights_count
            if rights_count >= mil.target_value and not mil.reached_at:
                mil.reached_at = datetime.utcnow()
                self.user_stats_points[user_id] += mil.points
                newly_reached.append(mil.to_dict())
        
        # Quality milestones
        quality_mils = ['avg_quality_80', 'avg_quality_90']
        for mil_id in quality_mils:
            mil = user_mils[mil_id]
            mil.current_value = int(avg_quality)
            if avg_quality >= mil.target_value and not mil.reached_at:
                mil.reached_at = datetime.utcnow()
                self.user_stats_points[user_id] += mil.points
                newly_reached.append(mil.to_dict())
        
        return newly_reached
    
    def get_user_stats_points(self, user_id: str) -> int:
        """Get total statistics points for a user"""
        return self.user_stats_points.get(user_id, 0)
    
    def update_user_stats(self, user_id: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user stats and check for new achievements/milestones
        Returns dict with newly earned items and updated points
        """
        new_achievements = self.check_and_award_achievements(user_id, stats)
        new_milestones = self.check_and_award_milestones(user_id, stats)
        total_points = self.get_user_stats_points(user_id)
        
        return {
            'new_achievements': new_achievements,
            'new_milestones': new_milestones,
            'total_stats_points': total_points,
            'total_earned_points': sum(ach.get('points', 0) for ach in new_achievements) + 
                                  sum(mil.get('points', 0) for mil in new_milestones)
        }


# Global instance
game_achievement_system = GameAchievementSystem()

