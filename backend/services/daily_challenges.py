"""
Daily Challenges & Quests System
Provides daily, weekly, and special event challenges
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from collections import defaultdict


class Challenge:
    """Represents a single challenge"""
    
    def __init__(self, challenge_id: str, name: str, description: str,
                 challenge_type: str, target_value: int, reward_xp: int,
                 reward_items: List[str] = None, difficulty: str = 'normal',
                 category: str = 'general', icon: str = '🎯'):
        self.id = challenge_id
        self.name = name
        self.description = description
        self.type = challenge_type  # daily, weekly, event
        self.target_value = target_value
        self.reward_xp = reward_xp
        self.reward_items = reward_items or []
        self.difficulty = difficulty  # easy, normal, hard, expert
        self.category = category
        self.icon = icon
        self.completed_at = None
        self.progress = 0
        self.started_at = None
        self.expires_at = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'target_value': self.target_value,
            'reward_xp': self.reward_xp,
            'reward_items': self.reward_items,
            'difficulty': self.difficulty,
            'category': self.category,
            'icon': self.icon,
            'completed': self.completed_at is not None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'progress': self.progress,
            'progress_percent': min(100, int((self.progress / self.target_value) * 100)) if self.target_value > 0 else 0,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'time_remaining': self._get_time_remaining()
        }
    
    def _get_time_remaining(self) -> Optional[str]:
        """Get time remaining until expiration"""
        if not self.expires_at:
            return None
        if datetime.utcnow() >= self.expires_at:
            return "Expired"
        remaining = self.expires_at - datetime.utcnow()
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        return f"{remaining.days}d {hours}h {minutes}m"


class DailyChallengeSystem:
    """Manages daily challenges and quests"""
    
    def __init__(self):
        """Initialize challenge system"""
        self.challenges = {}
        self.user_challenges = {}  # {user_id: {challenge_id: Challenge}}
        self.user_progress = {}  # {user_id: {challenge_id: progress}}
        self._initialize_challenges()
    
    def _initialize_challenges(self):
        """Initialize all available challenges"""
        # Daily challenges
        daily_challenges = [
            Challenge(
                'daily_video_1',
                'Daglig Video #1',
                'Opret 1 video i dag',
                'daily',
                1,
                150,
                ['theme_unlock:basic'],
                'easy',
                'generation',
                '🎬'
            ),
            Challenge(
                'daily_video_3',
                'Video Mester',
                'Opret 3 videoer i dag',
                'daily',
                3,
                300,
                ['xp_boost:1.5x:24h'],
                'normal',
                'generation',
                '🎥'
            ),
            Challenge(
                'daily_quality',
                'Kvalitets Jæger',
                'Opret en video med kvalitetsscore >= 0.8',
                'daily',
                1,
                250,
                ['stat_point:1'],
                'normal',
                'quality',
                '⭐'
            ),
            Challenge(
                'daily_category',
                'Kategori Ekspert',
                'Opret videoer i 2 forskellige kategorier',
                'daily',
                2,
                200,
                [],
                'normal',
                'category',
                '📁'
            ),
            Challenge(
                'daily_perfect',
                'Perfektionist',
                'Opret en video med perfekt kvalitet (1.0)',
                'daily',
                1,
                500,
                ['rare_badge:perfectionist', 'stat_point:2'],
                'hard',
                'quality',
                '💎'
            ),
        ]
        
        # Weekly challenges
        weekly_challenges = [
            Challenge(
                'weekly_video_10',
                'Ugentlig Produktion',
                'Opret 10 videoer denne uge',
                'weekly',
                10,
                1000,
                ['theme_unlock:premium', 'xp_boost:2x:48h'],
                'normal',
                'generation',
                '📊'
            ),
            Challenge(
                'weekly_quality',
                'Kvalitets Mester',
                'Opret 5 videoer med kvalitetsscore >= 0.9',
                'weekly',
                5,
                1500,
                ['rare_badge:quality_master', 'stat_point:5'],
                'hard',
                'quality',
                '🏆'
            ),
            Challenge(
                'weekly_all_categories',
                'Kategori Eksplorer',
                'Opret videoer i alle kategorier',
                'weekly',
                3,
                1200,
                ['theme_unlock:all', 'xp_boost:1.5x:72h'],
                'normal',
                'category',
                '🗺️'
            ),
            Challenge(
                'weekly_level_up',
                'Niveau Stiger',
                'Stig 2 niveauer denne uge',
                'weekly',
                2,
                2000,
                ['rare_badge:level_master', 'stat_point:10'],
                'hard',
                'leveling',
                '📈'
            ),
        ]
        
        # Add all challenges
        for challenge in daily_challenges + weekly_challenges:
            self.challenges[challenge.id] = challenge
    
    def get_daily_challenges(self, user_id: str) -> List[Dict]:
        """Get active daily challenges for user"""
        today = date.today()
        user_challenges = self.user_challenges.get(user_id, {})
        
        # Generate new daily challenges if needed
        active_daily = []
        for challenge_id, challenge in self.challenges.items():
            if challenge.type == 'daily':
                user_challenge = user_challenges.get(challenge_id)
                
                # Check if challenge needs refresh
                if not user_challenge or (user_challenge.completed_at and user_challenge.completed_at.date() < today):
                    # Create new instance for today
                    new_challenge = Challenge(
                        challenge.id,
                        challenge.name,
                        challenge.description,
                        challenge.type,
                        challenge.target_value,
                        challenge.reward_xp,
                        challenge.reward_items,
                        challenge.difficulty,
                        challenge.category,
                        challenge.icon
                    )
                    new_challenge.started_at = datetime.utcnow()
                    new_challenge.expires_at = datetime.utcnow() + timedelta(days=1)
                    new_challenge.progress = self.user_progress.get(user_id, {}).get(challenge_id, 0)
                    
                    if user_challenge and user_challenge.completed_at and user_challenge.completed_at.date() < today:
                        new_challenge.progress = 0  # Reset for new day
                    
                    active_daily.append(new_challenge)
                    if user_id not in self.user_challenges:
                        self.user_challenges[user_id] = {}
                    self.user_challenges[user_id][challenge_id] = new_challenge
                else:
                    active_daily.append(user_challenge)
        
        return [c.to_dict() for c in active_daily]
    
    def get_weekly_challenges(self, user_id: str) -> List[Dict]:
        """Get active weekly challenges for user"""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        user_challenges = self.user_challenges.get(user_id, {})
        
        # Generate new weekly challenges if needed
        active_weekly = []
        for challenge_id, challenge in self.challenges.items():
            if challenge.type == 'weekly':
                user_challenge = user_challenges.get(challenge_id)
                
                # Check if challenge needs refresh (new week)
                if not user_challenge or (user_challenge.started_at and user_challenge.started_at.date() < week_start):
                    # Create new instance for this week
                    new_challenge = Challenge(
                        challenge.id,
                        challenge.name,
                        challenge.description,
                        challenge.type,
                        challenge.target_value,
                        challenge.reward_xp,
                        challenge.reward_items,
                        challenge.difficulty,
                        challenge.category,
                        challenge.icon
                    )
                    new_challenge.started_at = datetime.utcnow()
                    new_challenge.expires_at = datetime.utcnow() + timedelta(days=7)
                    new_challenge.progress = 0  # Reset for new week
                    
                    active_weekly.append(new_challenge)
                    if user_id not in self.user_challenges:
                        self.user_challenges[user_id] = {}
                    self.user_challenges[user_id][challenge_id] = new_challenge
                else:
                    active_weekly.append(user_challenge)
        
        return [c.to_dict() for c in active_weekly]
    
    def update_challenge_progress(self, user_id: str, challenge_id: str, 
                                 progress_increment: int = 1) -> Dict[str, Any]:
        """Update challenge progress and check for completion"""
        if user_id not in self.user_challenges:
            self.user_challenges[user_id] = {}
        
        if challenge_id not in self.user_challenges[user_id]:
            # Initialize challenge
            base_challenge = self.challenges.get(challenge_id)
            if not base_challenge:
                return {'success': False, 'error': 'Challenge not found'}
            
            new_challenge = Challenge(
                base_challenge.id,
                base_challenge.name,
                base_challenge.description,
                base_challenge.type,
                base_challenge.target_value,
                base_challenge.reward_xp,
                base_challenge.reward_items,
                base_challenge.difficulty,
                base_challenge.category,
                base_challenge.icon
            )
            new_challenge.started_at = datetime.utcnow()
            if base_challenge.type == 'daily':
                new_challenge.expires_at = datetime.utcnow() + timedelta(days=1)
            elif base_challenge.type == 'weekly':
                new_challenge.expires_at = datetime.utcnow() + timedelta(days=7)
            
            self.user_challenges[user_id][challenge_id] = new_challenge
        
        challenge = self.user_challenges[user_id][challenge_id]
        
        # Check if expired
        if challenge.expires_at and datetime.utcnow() >= challenge.expires_at:
            return {'success': False, 'error': 'Challenge expired'}
        
        # Check if already completed
        if challenge.completed_at:
            return {'success': True, 'completed': True, 'message': 'Already completed'}
        
        # Update progress
        challenge.progress += progress_increment
        
        # Check for completion
        completed = False
        rewards = {}
        if challenge.progress >= challenge.target_value:
            challenge.completed_at = datetime.utcnow()
            completed = True
            rewards = {
                'xp': challenge.reward_xp,
                'items': challenge.reward_items
            }
        
        return {
            'success': True,
            'completed': completed,
            'progress': challenge.progress,
            'target': challenge.target_value,
            'progress_percent': min(100, int((challenge.progress / challenge.target_value) * 100)),
            'rewards': rewards if completed else None
        }
    
    def get_user_challenges_summary(self, user_id: str) -> Dict[str, Any]:
        """Get summary of all user challenges"""
        daily = self.get_daily_challenges(user_id)
        weekly = self.get_weekly_challenges(user_id)
        
        daily_completed = sum(1 for c in daily if c.get('completed'))
        weekly_completed = sum(1 for c in weekly if c.get('completed'))
        
        total_rewards_xp = sum(c.get('reward_xp', 0) for c in daily + weekly if c.get('completed'))
        
        return {
            'daily': {
                'total': len(daily),
                'completed': daily_completed,
                'remaining': len(daily) - daily_completed
            },
            'weekly': {
                'total': len(weekly),
                'completed': weekly_completed,
                'remaining': len(weekly) - weekly_completed
            },
            'total_rewards_xp': total_rewards_xp,
            'challenges': {
                'daily': daily,
                'weekly': weekly
            }
        }


# Global instance
daily_challenge_system = DailyChallengeSystem()

