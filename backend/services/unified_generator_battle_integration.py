"""
Unified Generator and Quick Battle Integration Service
Makes both systems work together seamlessly with Epic Gaming Experience
"""
from typing import Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class UnifiedGeneratorBattleIntegration:
    """
    Unified service that integrates video generation and quick battle systems
    Ensures both work together with Epic Gaming Experience tracking
    """
    
    def __init__(self):
        self.generator_service = None
        self.quick_battle_service = None
        self.epic_gaming_service = None
        self._initialize_services()
    
    def _initialize_services(self):
        """Initialize all required services"""
        try:
            from backend.services.ai_video_clip_generator import ai_video_clip_generator
            self.generator_service = ai_video_clip_generator
            logger.info("[UnifiedIntegration] Generator service initialized")
        except Exception as e:
            logger.warning(f"[UnifiedIntegration] Generator service not available: {e}")
        
        try:
            from backend.services.quick_battle_system import quick_battle
            self.quick_battle_service = quick_battle
            logger.info("[UnifiedIntegration] Quick Battle service initialized")
        except Exception as e:
            logger.warning(f"[UnifiedIntegration] Quick Battle service not available: {e}")
        
        try:
            from backend.services.epic_gaming_experience import epic_gaming_experience
            self.epic_gaming_service = epic_gaming_experience
            logger.info("[UnifiedIntegration] Epic Gaming service initialized")
        except Exception as e:
            logger.warning(f"[UnifiedIntegration] Epic Gaming service not available: {e}")
    
    def generate_video_with_tracking(
        self,
        prompt: str,
        user_id: str = 'default_user',
        duration: int = 5,
        resolution: str = '1280x768',
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate video with Epic Gaming Experience tracking
        
        Args:
            prompt: Video generation prompt
            user_id: User identifier
            duration: Video duration in seconds
            resolution: Video resolution
            **kwargs: Additional generator parameters
            
        Returns:
            Generation result with tracking
        """
        try:
            # Track video generation activity
            if self.epic_gaming_service:
                self.epic_gaming_service.track_activity(
                    user_id,
                    'generate_video',
                    {
                        'prompt': prompt[:100],  # Truncate for metadata
                        'duration': duration,
                        'resolution': resolution
                    }
                )
            
            # Generate video
            if not self.generator_service:
                return {
                    'success': False,
                    'error': 'Generator service not available'
                }
            
            result = self.generator_service.generate_video_with_all_ai(
                prompt=prompt,
                user_id=user_id,
                duration=duration,
                resolution=resolution,
                **kwargs
            )
            
            # Track successful generation
            if result.get('success') and self.epic_gaming_service:
                self.epic_gaming_service.track_activity(
                    user_id,
                    'video_created',
                    {
                        'video_id': result.get('video_id'),
                        'duration': duration
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"[UnifiedIntegration] Error generating video: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_quick_battle_with_tracking(
        self,
        user_id: str = 'default_user',
        difficulty: str = 'balanced',
        opponent_type: str = 'ai'
    ) -> Dict[str, Any]:
        """
        Create quick battle with Epic Gaming Experience tracking
        
        Args:
            user_id: User identifier
            difficulty: Battle difficulty
            opponent_type: Type of opponent
            
        Returns:
            Battle creation result with tracking
        """
        try:
            # Track battle participation
            if self.epic_gaming_service:
                self.epic_gaming_service.track_activity(
                    user_id,
                    'battle_participate',
                    {
                        'battle_type': 'quick_battle',
                        'difficulty': difficulty,
                        'action': 'create'
                    }
                )
            
            # Create battle
            if not self.quick_battle_service:
                return {
                    'success': False,
                    'error': 'Quick Battle service not available'
                }
            
            result = self.quick_battle_service.create_quick_battle(
                user_id=user_id,
                difficulty=difficulty,
                opponent_type=opponent_type
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[UnifiedIntegration] Error creating battle: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def complete_battle_with_tracking(
        self,
        battle_id: str,
        user_id: str = 'default_user',
        won: bool = False,
        duration: float = 0.0,
        moves: int = 0
    ) -> Dict[str, Any]:
        """
        Complete battle with Epic Gaming Experience tracking
        
        Args:
            battle_id: Battle identifier
            user_id: User identifier
            won: Whether user won
            duration: Battle duration
            moves: Number of moves
            
        Returns:
            Completion result with tracking
        """
        try:
            # Complete battle
            if not self.quick_battle_service:
                return {
                    'success': False,
                    'error': 'Quick Battle service not available'
                }
            
            result = self.quick_battle_service.complete_battle(
                battle_id=battle_id,
                user_id=user_id,
                won=won,
                duration=duration,
                moves=moves
            )
            
            # Track battle completion
            if result.get('success') and self.epic_gaming_service:
                activity_type = 'battle_win' if won else 'battle_participate'
                self.epic_gaming_service.track_activity(
                    user_id,
                    activity_type,
                    {
                        'battle_id': battle_id,
                        'battle_type': 'quick_battle',
                        'duration': duration,
                        'moves': moves,
                        'result': 'win' if won else 'loss'
                    }
                )
            
            return result
            
        except Exception as e:
            logger.error(f"[UnifiedIntegration] Error completing battle: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_unified_stats(self, user_id: str = 'default_user') -> Dict[str, Any]:
        """
        Get unified stats for both generator and battle
        
        Args:
            user_id: User identifier
            
        Returns:
            Unified statistics
        """
        stats = {
            'user_id': user_id,
            'generator': {},
            'battle': {},
            'epic_gaming': {}
        }
        
        # Get generator stats
        if self.generator_service:
            try:
                # Get generated videos count
                generated_videos = getattr(self.generator_service, 'generated_videos', {})
                stats['generator'] = {
                    'videos_created': len([v for v in generated_videos.values() if v.get('user_id') == user_id]),
                    'total_videos': len(generated_videos)
                }
            except Exception as e:
                logger.warning(f"[UnifiedIntegration] Error getting generator stats: {e}")
        
        # Get battle stats
        if self.quick_battle_service:
            try:
                battle_stats = self.quick_battle_service.get_user_battle_stats(user_id)
                stats['battle'] = battle_stats
            except Exception as e:
                logger.warning(f"[UnifiedIntegration] Error getting battle stats: {e}")
        
        # Get Epic Gaming stats
        if self.epic_gaming_service:
            try:
                progress = self.epic_gaming_service.get_user_progress(user_id)
                stats['epic_gaming'] = {
                    'level': progress.get('level', 1),
                    'xp': progress.get('xp', 0),
                    'story_chapter': progress.get('story_chapter', 1)
                }
            except Exception as e:
                logger.warning(f"[UnifiedIntegration] Error getting Epic Gaming stats: {e}")
        
        return stats
    
    def check_services_status(self) -> Dict[str, bool]:
        """
        Check status of all integrated services
        
        Returns:
            Status of each service
        """
        return {
            'generator': self.generator_service is not None,
            'quick_battle': self.quick_battle_service is not None,
            'epic_gaming': self.epic_gaming_service is not None
        }


# Global instance
unified_integration = UnifiedGeneratorBattleIntegration()
