"""
Enhanced Game Agent Service
3 Agent Abilities: Automated Gameplay, Battle Automation, Content Generation
Tracks gaming experience and comprehensive activity metrics
"""
import os
import sys
import json
import time
import uuid
import random
import requests
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

class EnhancedGameAgent:
    """
    Enhanced Game Agent with 3 core abilities:
    1. Automated Gameplay - Play games, complete quests, daily challenges
    2. Battle Automation - Automated battles, win streaks, tournaments
    3. Content Generation - Generate clips and videos automatically
    
    Tracks gaming experience and comprehensive metrics
    """
    
    def __init__(self, agent_id: Optional[str] = None, base_url: str = 'https://masternoder.dk/vidgenerator', user_id: Optional[str] = None):
        self.agent_id = agent_id or f"agent_{uuid.uuid4().hex[:12]}"
        self.base_url = base_url
        self.user_id = user_id or f"user_{self.agent_id}"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': f'EnhancedGameAgent/{self.agent_id}',
            'Content-Type': 'application/json'
        })
        
        # Enhanced stats with gaming experience tracking
        self.stats = {
            # Battle stats
            'battles_created': 0,
            'battles_won': 0,
            'battles_lost': 0,
            'battle_streak': 0,
            'tournaments_joined': 0,
            'tournaments_won': 0,
            
            # Gameplay stats
            'quests_completed': 0,
            'daily_challenges_completed': 0,
            'achievements_unlocked': 0,
            'levels_gained': 0,
            
            # Content generation stats
            'videos_generated': 0,
            'clips_generated': 0,
            'total_generation_time': 0,
            
            # URL testing
            'urls_tested': 0,
            'urls_success': 0,
            'urls_failed': 0,
            
            # Points earned
            'points_earned': {},
            'total_points_earned': 0,
            
            # Gaming experience
            'gaming_experience': 0,
            'experience_multiplier': 1.0,
            'activity_score': 0,
            
            # Activity tracking
            'start_time': datetime.now(),
            'last_action': None,
            'action_history': [],
            'session_duration': 0
        }
        
        self.active_battles = {}
        self.active_quests = []
        
    # ========================================================================
    # ABILITY 1: AUTOMATED GAMEPLAY
    # ========================================================================
    
    def automated_gameplay(self, duration_minutes: int = 10, action_interval: int = 30) -> Dict[str, Any]:
        """
        Ability 1: Automated Gameplay
        Plays the game by completing quests, daily challenges, earning achievements
        
        Args:
            duration_minutes: How long to play (minutes)
            action_interval: Seconds between actions
            
        Returns:
            Activity summary
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        actions_performed = 0
        experience_gained = 0
        
        logger.info(f"[Agent {self.agent_id}] Starting automated gameplay for {duration_minutes} minutes")
        
        while datetime.now() < end_time:
            try:
                # Randomly choose an action
                action = random.choice([
                    'complete_quest',
                    'complete_daily_challenge',
                    'check_achievements',
                    'earn_activity_points'
                ])
                
                if action == 'complete_quest':
                    result = self._complete_random_quest()
                    if result.get('success'):
                        actions_performed += 1
                        experience_gained += 10
                        
                elif action == 'complete_daily_challenge':
                    result = self._complete_daily_challenge()
                    if result.get('success'):
                        actions_performed += 1
                        experience_gained += 15
                        
                elif action == 'check_achievements':
                    result = self._check_and_claim_achievements()
                    if result.get('success'):
                        actions_performed += 1
                        experience_gained += 20
                        
                elif action == 'earn_activity_points':
                    result = self._earn_activity_points()
                    if result.get('success'):
                        actions_performed += 1
                        experience_gained += 5
                
                # Update gaming experience
                self.stats['gaming_experience'] += experience_gained
                self.stats['activity_score'] += experience_gained
                
                # Wait before next action
                time.sleep(action_interval)
                
            except Exception as e:
                logger.error(f"[Agent {self.agent_id}] Error in automated gameplay: {e}")
                time.sleep(action_interval)
        
        duration = (datetime.now() - start_time).total_seconds()
        self.stats['session_duration'] += duration
        
        return {
            'success': True,
            'ability': 'automated_gameplay',
            'duration_minutes': duration_minutes,
            'actions_performed': actions_performed,
            'experience_gained': experience_gained,
            'gaming_experience': self.stats['gaming_experience'],
            'activity_score': self.stats['activity_score']
        }
    
    def _complete_random_quest(self) -> Dict[str, Any]:
        """Complete a random quest"""
        try:
            # Get active quests
            response = self.session.get(f"{self.base_url}/api/game-mechanics/quests", params={'user_id': self.user_id}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('quests'):
                    quest = random.choice(data['quests'])
                    if quest.get('status') == 'active':
                        # Complete quest
                        complete_response = self.session.post(
                            f"{self.base_url}/api/game-mechanics/quest/complete",
                            json={'user_id': self.user_id, 'quest_id': quest['quest_id']},
                            timeout=10
                        )
                        if complete_response.status_code == 200:
                            self.stats['quests_completed'] += 1
                            return {'success': True, 'quest_id': quest['quest_id']}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error completing quest: {e}")
            return {'success': False, 'error': str(e)}
    
    def _complete_daily_challenge(self) -> Dict[str, Any]:
        """Complete a daily challenge"""
        try:
            # Get daily challenges
            response = self.session.get(f"{self.base_url}/api/game-mechanics/daily-challenges", params={'user_id': self.user_id}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('challenges'):
                    challenge = random.choice([c for c in data['challenges'] if c.get('status') == 'active'])
                    if challenge:
                        # Complete challenge
                        complete_response = self.session.post(
                            f"{self.base_url}/api/game-mechanics/daily-challenge/complete",
                            json={'user_id': self.user_id, 'challenge_id': challenge['challenge_id']},
                            timeout=10
                        )
                        if complete_response.status_code == 200:
                            self.stats['daily_challenges_completed'] += 1
                            return {'success': True, 'challenge_id': challenge['challenge_id']}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error completing daily challenge: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_and_claim_achievements(self) -> Dict[str, Any]:
        """Check and claim achievements"""
        try:
            response = self.session.get(f"{self.base_url}/api/game/achievements", params={'user_id': self.user_id}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('achievements'):
                    unlocked = [a for a in data['achievements'] if a.get('unlocked') and not a.get('claimed')]
                    if unlocked:
                        self.stats['achievements_unlocked'] += len(unlocked)
                        return {'success': True, 'achievements_claimed': len(unlocked)}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
            return {'success': False, 'error': str(e)}
    
    def _earn_activity_points(self) -> Dict[str, Any]:
        """Earn activity points through various activities"""
        try:
            # Award comprehensive points for activity
            response = self.session.post(
                f"{self.base_url}/api/game-mechanics/award-points",
                json={
                    'user_id': self.user_id,
                    'action': 'time_played',
                    'difficulty': 'normal',
                    'multiplier': 1.0
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    return {'success': True, 'points': data.get('points_awarded', {})}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error earning activity points: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========================================================================
    # ABILITY 2: BATTLE AUTOMATION
    # ========================================================================
    
    def battle_automation(self, num_battles: int = 10, battle_type: str = 'quick', difficulty: str = 'balanced') -> Dict[str, Any]:
        """
        Ability 2: Battle Automation
        Automatically creates and executes battles, maintains win streaks, joins tournaments
        
        Args:
            num_battles: Number of battles to execute
            battle_type: Type of battle (quick, standard, tournament)
            difficulty: Difficulty level (easy, balanced, hard)
            
        Returns:
            Battle summary
        """
        battles_executed = 0
        battles_won = 0
        battles_lost = 0
        experience_gained = 0
        
        logger.info(f"[Agent {self.agent_id}] Starting battle automation: {num_battles} battles")
        
        for i in range(num_battles):
            try:
                # Create battle
                battle_result = self._create_battle(battle_type, difficulty)
                if not battle_result.get('success'):
                    continue
                
                battle_id = battle_result.get('battle_id')
                if not battle_id:
                    continue
                
                # Execute battle (60% win rate)
                won = random.random() > 0.4
                execute_result = self._execute_battle(battle_id, won)
                
                if execute_result.get('success'):
                    battles_executed += 1
                    if won:
                        battles_won += 1
                        self.stats['battle_streak'] += 1
                        experience_gained += 50
                    else:
                        battles_lost += 1
                        self.stats['battle_streak'] = 0
                        experience_gained += 10
                    
                    # Award comprehensive battle points
                    self._award_battle_points(won, battle_type, difficulty)
                
                # Small delay between battles
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"[Agent {self.agent_id}] Error in battle automation: {e}")
                time.sleep(2)
        
        # Update gaming experience
        self.stats['gaming_experience'] += experience_gained
        self.stats['battles_created'] += battles_executed
        self.stats['battles_won'] += battles_won
        self.stats['battles_lost'] += battles_lost
        
        return {
            'success': True,
            'ability': 'battle_automation',
            'battles_executed': battles_executed,
            'battles_won': battles_won,
            'battles_lost': battles_lost,
            'battle_streak': self.stats['battle_streak'],
            'experience_gained': experience_gained,
            'gaming_experience': self.stats['gaming_experience']
        }
    
    def _create_battle(self, battle_type: str, difficulty: str) -> Dict[str, Any]:
        """Create a battle"""
        try:
            endpoints = [
                '/api/quick-battle/create',
                '/api/unified/create-battle',
                '/api/game/battle/create'
            ]
            
            for endpoint in endpoints:
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json={
                        'user_id': self.user_id,
                        'battle_type': battle_type,
                        'difficulty': difficulty
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    if data.get('success'):
                        battle_id = data.get('battle_id') or data.get('result', {}).get('battle_id')
                        if battle_id:
                            return {'success': True, 'battle_id': battle_id}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error creating battle: {e}")
            return {'success': False, 'error': str(e)}
    
    def _execute_battle(self, battle_id: str, won: bool) -> Dict[str, Any]:
        """Execute/complete a battle"""
        try:
            endpoints = [
                '/api/quick-battle/complete',
                '/api/battle/battles/{}/action'.format(battle_id)
            ]
            
            for endpoint in endpoints:
                response = self.session.post(
                    f"{self.base_url}{endpoint}",
                    json={
                        'battle_id': battle_id,
                        'user_id': self.user_id,
                        'won': won,
                        'duration': random.uniform(30, 300),
                        'moves': random.randint(10, 50)
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return {'success': True, 'won': won}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error executing battle: {e}")
            return {'success': False, 'error': str(e)}
    
    def _award_battle_points(self, won: bool, battle_type: str, difficulty: str):
        """Award comprehensive battle points"""
        try:
            action = 'battle_win' if won else 'battle_loss'
            multiplier = 1.5 if self.stats['battle_streak'] >= 3 else 1.0
            
            response = self.session.post(
                f"{self.base_url}/api/game-mechanics/award-points",
                json={
                    'user_id': self.user_id,
                    'action': action,
                    'difficulty': difficulty,
                    'multiplier': multiplier
                },
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('points_awarded'):
                    self._update_points_earned(data['points_awarded'])
        except Exception as e:
            logger.error(f"Error awarding battle points: {e}")
    
    def join_tournament(self, tournament_id: str) -> Dict[str, Any]:
        """Join a tournament"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/battle/tournament/join",
                json={'tournament_id': tournament_id, 'user_id': self.user_id},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.stats['tournaments_joined'] += 1
                    return {'success': True}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error joining tournament: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========================================================================
    # ABILITY 3: CONTENT GENERATION
    # ========================================================================
    
    def content_generation(self, num_generations: int = 5, generation_type: str = 'clip') -> Dict[str, Any]:
        """
        Ability 3: Content Generation
        Automatically generate clips and videos
        
        Args:
            num_generations: Number of clips/videos to generate
            generation_type: 'clip' or 'video'
            
        Returns:
            Generation summary
        """
        generations_completed = 0
        total_time = 0
        experience_gained = 0
        
        logger.info(f"[Agent {self.agent_id}] Starting content generation: {num_generations} {generation_type}s")
        
        prompts = [
            "A beautiful sunset over mountains",
            "City lights at night",
            "Ocean waves crashing on beach",
            "Forest path in autumn",
            "Modern cityscape",
            "Desert landscape",
            "Mountain peak view",
            "Urban street scene"
        ]
        
        for i in range(num_generations):
            try:
                prompt = random.choice(prompts)
                start_time = time.time()
                
                if generation_type == 'clip':
                    result = self._generate_clip(prompt)
                else:
                    result = self._generate_video(prompt)
                
                elapsed = time.time() - start_time
                total_time += elapsed
                
                if result.get('success'):
                    generations_completed += 1
                    if generation_type == 'clip':
                        self.stats['clips_generated'] += 1
                    else:
                        self.stats['videos_generated'] += 1
                    experience_gained += 30
                    
                    # Points are automatically awarded by the generation endpoints
                
                # Small delay between generations
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"[Agent {self.agent_id}] Error in content generation: {e}")
                time.sleep(3)
        
        self.stats['total_generation_time'] += total_time
        self.stats['gaming_experience'] += experience_gained
        
        return {
            'success': True,
            'ability': 'content_generation',
            'generations_completed': generations_completed,
            'generation_type': generation_type,
            'total_time': total_time,
            'experience_gained': experience_gained,
            'gaming_experience': self.stats['gaming_experience']
        }
    
    def _generate_clip(self, prompt: str) -> Dict[str, Any]:
        """Generate a clip"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/ai-clips/generate",
                json={
                    'prompt': prompt,
                    'user_id': self.user_id,
                    'clip_count': 1,
                    'duration': 5
                },
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'result': data}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error generating clip: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_video(self, prompt: str) -> Dict[str, Any]:
        """Generate a video"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/ai-video/generate",
                json={
                    'prompt': prompt,
                    'user_id': self.user_id,
                    'duration': 10
                },
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'result': data}
            return {'success': False}
        except Exception as e:
            logger.error(f"Error generating video: {e}")
            return {'success': False, 'error': str(e)}
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _update_points_earned(self, points_awarded: Dict[str, Any]):
        """Update points earned tracking"""
        for point_type, amount in points_awarded.items():
            if point_type not in self.stats['points_earned']:
                self.stats['points_earned'][point_type] = 0
            self.stats['points_earned'][point_type] += amount
            self.stats['total_points_earned'] += amount
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive agent stats"""
        duration = (datetime.now() - self.stats['start_time']).total_seconds()
        return {
            'agent_id': self.agent_id,
            'user_id': self.user_id,
            'stats': self.stats.copy(),
            'session_duration_hours': duration / 3600,
            'gaming_experience_level': self._calculate_experience_level(),
            'activity_summary': self._get_activity_summary()
        }
    
    def _calculate_experience_level(self) -> str:
        """Calculate gaming experience level"""
        exp = self.stats['gaming_experience']
        if exp >= 10000:
            return 'Legendary'
        elif exp >= 5000:
            return 'Master'
        elif exp >= 2000:
            return 'Expert'
        elif exp >= 1000:
            return 'Advanced'
        elif exp >= 500:
            return 'Intermediate'
        else:
            return 'Beginner'
    
    def _get_activity_summary(self) -> Dict[str, Any]:
        """Get activity summary"""
        return {
            'total_actions': (
                self.stats['battles_created'] +
                self.stats['quests_completed'] +
                self.stats['daily_challenges_completed'] +
                self.stats['videos_generated'] +
                self.stats['clips_generated']
            ),
            'success_rate': (
                (self.stats['battles_won'] / max(self.stats['battles_created'], 1)) * 100
            ),
            'efficiency': (
                self.stats['gaming_experience'] / max(self.stats['session_duration'] / 3600, 0.1)
            )
        }
    
    def reset_stats(self):
        """Reset agent stats"""
        self.stats = {
            'battles_created': 0,
            'battles_won': 0,
            'battles_lost': 0,
            'battle_streak': 0,
            'tournaments_joined': 0,
            'tournaments_won': 0,
            'quests_completed': 0,
            'daily_challenges_completed': 0,
            'achievements_unlocked': 0,
            'levels_gained': 0,
            'videos_generated': 0,
            'clips_generated': 0,
            'total_generation_time': 0,
            'urls_tested': 0,
            'urls_success': 0,
            'urls_failed': 0,
            'points_earned': {},
            'total_points_earned': 0,
            'gaming_experience': 0,
            'experience_multiplier': 1.0,
            'activity_score': 0,
            'start_time': datetime.now(),
            'last_action': None,
            'action_history': [],
            'session_duration': 0
        }


# Global dictionary to hold agent instances
active_enhanced_agents: Dict[str, EnhancedGameAgent] = {}
