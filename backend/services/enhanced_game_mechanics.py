"""
Enhanced Game Mechanics - Comprehensive Point Earning System
Awards points from ALL unified point categories for competitive, fun progression
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import random
import logging

logger = logging.getLogger(__name__)


class EnhancedGameMechanics:
    """
    Enhanced Game Mechanics with comprehensive point earning
    Awards points from ALL unified point categories for competitive progression
    """
    
    def __init__(self):
        """Initialize enhanced game mechanics"""
        self.unified_points = None  # Will be injected
        self._active_quests = {}  # {user_id: [quests]}
        self._daily_challenges = {}  # {user_id: {date: [challenges]}}
        self._achievements_progress = {}  # {user_id: {achievement_id: progress}}
        self._streaks = {}  # {user_id: {streak_type: count}}
        self._tournaments = {}  # {tournament_id: tournament_data}
        self._seasons = {}  # {season_id: season_data}
        
    def set_unified_points(self, unified_points_system):
        """Inject unified points system"""
        self.unified_points = unified_points_system
    
    # ========================================================================
    # COMPREHENSIVE POINT EARNING - ALL CATEGORIES
    # ========================================================================
    
    def award_comprehensive_points(self, user_id: str, action: str, 
                                   difficulty: str = 'normal',
                                   multiplier: float = 1.0) -> Dict[str, Any]:
        """
        Award points from ALL categories based on action
        Creates competitive, fun progression gameplay
        
        Args:
            user_id: User identifier
            action: Action type (battle_win, battle_loss, quest_complete, daily_login, etc.)
            difficulty: Difficulty level (easy, normal, hard, extreme)
            multiplier: Point multiplier (streaks, bonuses, etc.)
            
        Returns:
            Result dictionary with all points awarded
        """
        if not self.unified_points:
            return {'success': False, 'error': 'Unified points system not available'}
        
        # Base points by difficulty
        difficulty_multipliers = {
            'easy': 0.5,
            'normal': 1.0,
            'hard': 2.0,
            'extreme': 5.0,
            'legendary': 10.0
        }
        diff_mult = difficulty_multipliers.get(difficulty, 1.0)
        final_multiplier = multiplier * diff_mult
        
        # Award points from ALL categories
        points_awarded = {}
        
        try:
            # ================================================================
            # CORE POINTS (XP, Level, Prestige)
            # ================================================================
            if action in ['battle_win', 'quest_complete', 'achievement_unlock']:
                xp_base = random.randint(50, 200) * final_multiplier
                result = self.unified_points.add_points(
                    user_id, 'CORE', 'xp', xp_base, f'{action}_core'
                )
                if result.get('success'):
                    points_awarded['xp'] = xp_base
                    
                # Check for level up
                level_up_result = self._check_level_up(user_id, xp_base)
                if level_up_result.get('level_up'):
                    points_awarded['level_up'] = True
                    points_awarded['new_level'] = level_up_result.get('new_level')
                    
                    # Bonus points for leveling up
                    bonus_coins = random.randint(100, 500) * final_multiplier
                    self.unified_points.add_points(
                        user_id, 'ECONOMY', 'coins', bonus_coins, 'level_up_bonus'
                    )
                    points_awarded['level_up_bonus_coins'] = bonus_coins
            
            # ================================================================
            # ECONOMY POINTS (Coins, Credits, Tokens)
            # ================================================================
            if action == 'battle_win':
                coins = random.randint(20, 100) * final_multiplier
                credits = random.randint(10, 50) * final_multiplier
                tokens = random.randint(1, 5) * final_multiplier
                
                self.unified_points.add_points(user_id, 'ECONOMY', 'coins', coins, 'battle_win')
                self.unified_points.add_points(user_id, 'ECONOMY', 'credits', credits, 'battle_win')
                self.unified_points.add_points(user_id, 'ECONOMY', 'tokens', tokens, 'battle_win')
                
                points_awarded['coins'] = coins
                points_awarded['credits'] = credits
                points_awarded['tokens'] = tokens
                
            elif action == 'quest_complete':
                coins = random.randint(50, 200) * final_multiplier
                self.unified_points.add_points(user_id, 'ECONOMY', 'coins', coins, 'quest_complete')
                points_awarded['coins'] = coins
                
            elif action == 'daily_login':
                coins = random.randint(10, 50) * final_multiplier
                credits = random.randint(5, 25) * final_multiplier
                self.unified_points.add_points(user_id, 'ECONOMY', 'coins', coins, 'daily_login')
                self.unified_points.add_points(user_id, 'ECONOMY', 'credits', credits, 'daily_login')
                points_awarded['coins'] = coins
                points_awarded['credits'] = credits
            
            # ================================================================
            # STATS POINTS (Creativity, Efficiency, Quality, Knowledge, Social)
            # ================================================================
            if action == 'battle_win':
                # Battle wins improve efficiency and knowledge
                efficiency = random.randint(1, 5) * final_multiplier
                knowledge = random.randint(1, 5) * final_multiplier
                self.unified_points.add_points(user_id, 'STATS', 'efficiency', efficiency, 'battle_win')
                self.unified_points.add_points(user_id, 'STATS', 'knowledge', knowledge, 'battle_win')
                points_awarded['efficiency'] = efficiency
                points_awarded['knowledge'] = knowledge
                
            elif action == 'quest_complete':
                # Quest completion improves creativity and quality
                creativity = random.randint(1, 5) * final_multiplier
                quality = random.randint(1, 5) * final_multiplier
                self.unified_points.add_points(user_id, 'STATS', 'creativity', creativity, 'quest_complete')
                self.unified_points.add_points(user_id, 'STATS', 'quality', quality, 'quest_complete')
                points_awarded['creativity'] = creativity
                points_awarded['quality'] = quality
                
            elif action == 'social_interaction':
                # Social actions improve social stat
                social = random.randint(2, 10) * final_multiplier
                self.unified_points.add_points(user_id, 'STATS', 'social', social, 'social_interaction')
                points_awarded['social'] = social
            
            # ================================================================
            # ACHIEVEMENTS (Achievements, Trophies, Milestones)
            # ================================================================
            if action == 'achievement_unlock':
                achievement_points = random.randint(100, 500) * final_multiplier
                trophy_points = random.randint(50, 250) * final_multiplier
                self.unified_points.add_points(
                    user_id, 'ACHIEVEMENTS', 'achievements', 1, 'achievement_unlock'
                )
                self.unified_points.add_points(
                    user_id, 'ACHIEVEMENTS', 'achievement_points', achievement_points, 'achievement_unlock'
                )
                self.unified_points.add_points(
                    user_id, 'ACHIEVEMENTS', 'trophy_points', trophy_points, 'achievement_unlock'
                )
                points_awarded['achievement_points'] = achievement_points
                points_awarded['trophy_points'] = trophy_points
                
            elif action == 'milestone_reach':
                milestone_points = random.randint(200, 1000) * final_multiplier
                self.unified_points.add_points(
                    user_id, 'ACHIEVEMENTS', 'milestones', 1, 'milestone_reach'
                )
                self.unified_points.add_points(
                    user_id, 'ACHIEVEMENTS', 'milestone_points', milestone_points, 'milestone_reach'
                )
                points_awarded['milestone_points'] = milestone_points
            
            # ================================================================
            # ACTIVITY (Videos, Generations, Time Played, Login Streak)
            # ================================================================
            if action == 'video_create':
                self.unified_points.add_points(user_id, 'ACTIVITY', 'videos', 1, 'video_create')
                points_awarded['videos'] = 1
                
            elif action == 'generation_complete':
                self.unified_points.add_points(user_id, 'ACTIVITY', 'generations', 1, 'generation_complete')
                points_awarded['generations'] = 1
                
            elif action == 'time_played':
                minutes = int(final_multiplier)
                self.unified_points.add_points(user_id, 'ACTIVITY', 'time_played', minutes, 'time_played')
                points_awarded['time_played'] = minutes
                
            elif action == 'daily_login':
                # Update login streak
                streak = self._update_streak(user_id, 'login')
                self.unified_points.set_points(user_id, 'ACTIVITY', 'login_streak', streak)
                self.unified_points.add_points(user_id, 'ACTIVITY', 'daily_logins', 1, 'daily_login')
                points_awarded['login_streak'] = streak
                points_awarded['daily_logins'] = 1
                
                # Streak bonus
                if streak >= 7:
                    streak_bonus = streak * 10 * final_multiplier
                    self.unified_points.add_points(
                        user_id, 'ECONOMY', 'coins', streak_bonus, 'streak_bonus'
                    )
                    points_awarded['streak_bonus'] = streak_bonus
            
            # ================================================================
            # BATTLE (Battle Wins, Battle Points, Battle Streak)
            # ================================================================
            if action == 'battle_win':
                battle_points = random.randint(10, 50) * final_multiplier
                streak = self._update_streak(user_id, 'battle')
                
                self.unified_points.add_points(user_id, 'BATTLE', 'battle_wins', 1, 'battle_win')
                self.unified_points.add_points(user_id, 'BATTLE', 'battle_points', battle_points, 'battle_win')
                self.unified_points.set_points(user_id, 'BATTLE', 'battle_streak', streak)
                
                points_awarded['battle_points'] = battle_points
                points_awarded['battle_streak'] = streak
                
                # Win streak bonus
                if streak >= 3:
                    streak_bonus = streak * 5 * final_multiplier
                    self.unified_points.add_points(
                        user_id, 'BATTLE', 'battle_points', streak_bonus, 'win_streak_bonus'
                    )
                    points_awarded['win_streak_bonus'] = streak_bonus
                    
            elif action == 'battle_loss':
                # Even losses give some points for participation
                participation_points = random.randint(1, 10) * final_multiplier
                self.unified_points.add_points(
                    user_id, 'BATTLE', 'battle_points', participation_points, 'battle_loss'
                )
                points_awarded['battle_points'] = participation_points
                self._reset_streak(user_id, 'battle')
                
            # ================================================================
            # SOCIAL (Friends, Followers, Chat, Social Interactions)
            # ================================================================
            if action == 'friend_add':
                self.unified_points.add_points(user_id, 'SOCIAL', 'friends', 1, 'friend_add')
                points_awarded['friends'] = 1
                
            elif action == 'follower_gain':
                self.unified_points.add_points(user_id, 'SOCIAL', 'followers', 1, 'follower_gain')
                points_awarded['followers'] = 1
                
            elif action == 'chat_message':
                chat_points = random.randint(1, 5) * final_multiplier
                self.unified_points.add_points(user_id, 'SOCIAL', 'chat_messages', 1, 'chat_message')
                self.unified_points.add_points(user_id, 'SOCIAL', 'chat_points', chat_points, 'chat_message')
                points_awarded['chat_points'] = chat_points
                
            elif action == 'social_interaction':
                self.unified_points.add_points(
                    user_id, 'SOCIAL', 'social_interactions', 1, 'social_interaction'
                )
                points_awarded['social_interactions'] = 1
            
            # ================================================================
            # METAL (Territory, Sex Metal, Porno Rights, MTG, Trophy Hunt)
            # ================================================================
            if action == 'territory_conquer':
                territory_points = random.randint(10, 50) * final_multiplier
                self.unified_points.add_points(
                    user_id, 'METAL', 'territory', territory_points, 'territory_conquer'
                )
                points_awarded['territory_points'] = territory_points
                
            elif action == 'trophy_collect':
                trophy_points = random.randint(5, 25) * final_multiplier
                self.unified_points.add_points(
                    user_id, 'METAL', 'trophy_hunt', trophy_points, 'trophy_collect'
                )
                points_awarded['trophy_hunt_points'] = trophy_points
            
            # ================================================================
            # RESOURCES (Energy, Materials, Knowledge, Technology)
            # ================================================================
            if action in ['battle_win', 'quest_complete']:
                energy = random.uniform(1.0, 5.0) * final_multiplier
                materials = random.uniform(0.5, 2.5) * final_multiplier
                knowledge = random.uniform(0.5, 3.0) * final_multiplier
                technology = random.uniform(0.3, 1.5) * final_multiplier
                
                self.unified_points.add_points(user_id, 'RESOURCES', 'energy', energy, action)
                self.unified_points.add_points(user_id, 'RESOURCES', 'materials', materials, action)
                self.unified_points.add_points(user_id, 'RESOURCES', 'knowledge', knowledge, action)
                self.unified_points.add_points(user_id, 'RESOURCES', 'technology', technology, action)
                
                points_awarded['energy'] = energy
                points_awarded['materials'] = materials
                points_awarded['resource_knowledge'] = knowledge
                points_awarded['technology'] = technology
            
            return {
                'success': True,
                'user_id': user_id,
                'action': action,
                'difficulty': difficulty,
                'multiplier': final_multiplier,
                'points_awarded': points_awarded,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error awarding comprehensive points: {e}", exc_info=True)
            return {'success': False, 'error': str(e), 'points_awarded': points_awarded}
    
    # ========================================================================
    # STREAK MANAGEMENT
    # ========================================================================
    
    def _update_streak(self, user_id: str, streak_type: str) -> int:
        """Update streak count for user"""
        if user_id not in self._streaks:
            self._streaks[user_id] = {}
        if streak_type not in self._streaks[user_id]:
            self._streaks[user_id][streak_type] = 0
        self._streaks[user_id][streak_type] += 1
        return self._streaks[user_id][streak_type]
    
    def _reset_streak(self, user_id: str, streak_type: str):
        """Reset streak count"""
        if user_id in self._streaks and streak_type in self._streaks[user_id]:
            self._streaks[user_id][streak_type] = 0
    
    def get_streak(self, user_id: str, streak_type: str) -> int:
        """Get current streak"""
        if user_id in self._streaks and streak_type in self._streaks[user_id]:
            return self._streaks[user_id][streak_type]
        return 0
    
    # ========================================================================
    # LEVEL UP CHECK
    # ========================================================================
    
    def _check_level_up(self, user_id: str, xp_gained: float) -> Dict[str, Any]:
        """Check if user leveled up"""
        try:
            points = self.unified_points.get_user_points(user_id)
            current_xp = points.get('xp', 0)
            current_level = points.get('level', 1)
            
            # Calculate XP needed for next level (simplified formula)
            xp_needed = 1000 * current_level * (1 + current_level * 0.1)
            
            if current_xp >= xp_needed:
                new_level = current_level + 1
                self.unified_points.set_points(user_id, 'CORE', 'level', new_level)
                return {'level_up': True, 'new_level': new_level, 'previous_level': current_level}
            
            return {'level_up': False, 'current_level': current_level}
        except:
            return {'level_up': False}
    
    # ========================================================================
    # QUEST SYSTEM
    # ========================================================================
    
    def create_quest(self, user_id: str, quest_type: str, 
                     difficulty: str = 'normal') -> Dict[str, Any]:
        """Create a new quest for user"""
        quest_id = f"quest_{user_id}_{datetime.utcnow().timestamp()}"
        
        quest_templates = {
            'daily_battle': {
                'name': 'Daily Battle Challenge',
                'description': 'Win 3 battles today',
                'target': 3,
                'current': 0,
                'reward_points': 500,
                'reward_category': 'ECONOMY',
                'reward_type': 'coins'
            },
            'win_streak': {
                'name': 'Win Streak Master',
                'description': 'Win 5 battles in a row',
                'target': 5,
                'current': 0,
                'reward_points': 1000,
                'reward_category': 'BATTLE',
                'reward_type': 'battle_points'
            },
            'social_activity': {
                'name': 'Social Butterfly',
                'description': 'Send 10 chat messages',
                'target': 10,
                'current': 0,
                'reward_points': 300,
                'reward_category': 'SOCIAL',
                'reward_type': 'chat_points'
            }
        }
        
        quest = quest_templates.get(quest_type, {
            'name': f'Custom Quest ({quest_type})',
            'description': 'Complete this quest',
            'target': 1,
            'current': 0,
            'reward_points': 100,
            'reward_category': 'CORE',
            'reward_type': 'xp'
        })
        
        quest.update({
            'quest_id': quest_id,
            'user_id': user_id,
            'type': quest_type,
            'difficulty': difficulty,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat()
        })
        
        if user_id not in self._active_quests:
            self._active_quests[user_id] = []
        self._active_quests[user_id].append(quest)
        
        return {'success': True, 'quest': quest}
    
    def complete_quest(self, user_id: str, quest_id: str) -> Dict[str, Any]:
        """Complete a quest and award rewards"""
        if user_id not in self._active_quests:
            return {'success': False, 'error': 'No active quests'}
        
        quest = None
        for q in self._active_quests[user_id]:
            if q['quest_id'] == quest_id:
                quest = q
                break
        
        if not quest:
            return {'success': False, 'error': 'Quest not found'}
        
        if quest['status'] != 'active':
            return {'success': False, 'error': 'Quest not active'}
        
        # Award rewards
        result = self.unified_points.add_points(
            user_id,
            quest['reward_category'],
            quest['reward_type'],
            quest['reward_points'],
            f'quest_complete_{quest_id}'
        )
        
        # Award comprehensive points
        comprehensive = self.award_comprehensive_points(
            user_id, 'quest_complete', quest.get('difficulty', 'normal')
        )
        
        # Mark quest as complete
        quest['status'] = 'completed'
        quest['completed_at'] = datetime.utcnow().isoformat()
        
        return {
            'success': True,
            'quest': quest,
            'reward_result': result,
            'comprehensive_points': comprehensive
        }
    
    def get_active_quests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active quests for user"""
        if user_id not in self._active_quests:
            return []
        return [q for q in self._active_quests[user_id] if q['status'] == 'active']
    
    # ========================================================================
    # DAILY CHALLENGES
    # ========================================================================
    
    def generate_daily_challenges(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate daily challenges for user"""
        today = datetime.utcnow().date().isoformat()
        
        if user_id not in self._daily_challenges:
            self._daily_challenges[user_id] = {}
        
        if today in self._daily_challenges[user_id]:
            return self._daily_challenges[user_id][today]
        
        challenges = [
            {
                'challenge_id': f"daily_{user_id}_{today}_1",
                'name': 'First Victory',
                'description': 'Win your first battle today',
                'type': 'battle_win',
                'target': 1,
                'current': 0,
                'reward_multiplier': 1.5,
                'status': 'active'
            },
            {
                'challenge_id': f"daily_{user_id}_{today}_2",
                'name': 'Social Activity',
                'description': 'Interact with 5 players today',
                'type': 'social_interaction',
                'target': 5,
                'current': 0,
                'reward_multiplier': 2.0,
                'status': 'active'
            },
            {
                'challenge_id': f"daily_{user_id}_{today}_3",
                'name': 'Quest Master',
                'description': 'Complete 3 quests today',
                'type': 'quest_complete',
                'target': 3,
                'current': 0,
                'reward_multiplier': 1.5,
                'status': 'active'
            }
        ]
        
        self._daily_challenges[user_id][today] = challenges
        return challenges
    
    def complete_daily_challenge(self, user_id: str, challenge_id: str) -> Dict[str, Any]:
        """Complete a daily challenge"""
        today = datetime.utcnow().date().isoformat()
        
        if user_id not in self._daily_challenges or today not in self._daily_challenges[user_id]:
            return {'success': False, 'error': 'No daily challenges found'}
        
        challenge = None
        for c in self._daily_challenges[user_id][today]:
            if c['challenge_id'] == challenge_id:
                challenge = c
                break
        
        if not challenge:
            return {'success': False, 'error': 'Challenge not found'}
        
        challenge['status'] = 'completed'
        challenge['completed_at'] = datetime.utcnow().isoformat()
        
        # Award points with multiplier
        result = self.award_comprehensive_points(
            user_id,
            challenge['type'],
            'normal',
            challenge['reward_multiplier']
        )
        
        return {'success': True, 'challenge': challenge, 'points_awarded': result}


# Global instance
enhanced_game_mechanics = EnhancedGameMechanics()
