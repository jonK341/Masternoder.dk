"""
Video/Clip Generation Rewards
Treated like other activities with unified point system
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class VideoGenerationRewards:
    """Manages rewards for video and clip generation"""
    
    def __init__(self):
        self.base_video_reward = 600  # video_generation points
        self.base_clip_reward = 300   # clip_generation points
        
        self.quality_multipliers = {
            'low': 0.5,
            'medium': 1.0,
            'high': 1.5,
            'premium': 2.0,
            'ultra': 2.5
        }
        
        self.innovation_bonuses = {
            'standard': 0,
            'creative': 0.5,
            'innovative': 1.0,
            'revolutionary': 2.0
        }
        
        self.viral_multipliers = {
            'normal': 1.0,
            'trending': 2.0,
            'viral': 3.0,
            'mega_viral': 5.0
        }
        
        self.generation_history = {}  # user_id -> [generations]
    
    def award_video_generation(self, user_id: str, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Award points for video generation"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            # Base reward
            base_points = self.base_video_reward
            
            # Quality bonus
            quality = video_data.get('quality', 'medium')
            quality_multiplier = self.quality_multipliers.get(quality, 1.0)
            
            # Innovation bonus
            innovation_level = video_data.get('innovation', 'standard')
            innovation_bonus = self.innovation_bonuses.get(innovation_level, 0)
            
            # Viral bonus
            viral_status = video_data.get('viral_status', 'normal')
            viral_multiplier = self.viral_multipliers.get(viral_status, 1.0)
            
            # Collaboration bonus
            is_collaboration = video_data.get('collaboration', False)
            collaboration_bonus = 0.25 if is_collaboration else 0
            
            # Calculate total points
            total_multiplier = quality_multiplier * (1 + innovation_bonus) * viral_multiplier * (1 + collaboration_bonus)
            total_points = int(base_points * total_multiplier)
            
            # Award points
            unified_points_db.add_points(
                user_id,
                'video_generation',
                total_points,
                source='video_generation_activity'
            )
            
            # Also award activity points (treat like other activities)
            activity_points = int(total_points * 0.1)  # 10% as activity points
            unified_points_db.add_points(
                user_id,
                'activity',
                activity_points,
                source='video_generation_activity'
            )
            
            # Track generation
            if user_id not in self.generation_history:
                self.generation_history[user_id] = []
            
            generation_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'video',
                'points_awarded': total_points,
                'video_data': video_data
            }
            self.generation_history[user_id].append(generation_entry)
            
            return {
                'success': True,
                'user_id': user_id,
                'base_points': base_points,
                'quality_multiplier': quality_multiplier,
                'innovation_bonus': innovation_bonus,
                'viral_multiplier': viral_multiplier,
                'collaboration_bonus': collaboration_bonus,
                'total_multiplier': total_multiplier,
                'video_generation_points': total_points,
                'activity_points': activity_points,
                'total_points': total_points + activity_points
            }
        except Exception as e:
            logger.error(f"Error awarding video generation: {e}")
            return {'success': False, 'error': str(e)}
    
    def award_clip_generation(self, user_id: str, clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Award points for clip generation"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            # Base reward
            base_points = self.base_clip_reward
            
            # Apply same bonuses as video
            quality = clip_data.get('quality', 'medium')
            quality_multiplier = self.quality_multipliers.get(quality, 1.0)
            
            innovation_level = clip_data.get('innovation', 'standard')
            innovation_bonus = self.innovation_bonuses.get(innovation_level, 0)
            
            viral_status = clip_data.get('viral_status', 'normal')
            viral_multiplier = self.viral_multipliers.get(viral_status, 1.0)
            
            is_collaboration = clip_data.get('collaboration', False)
            collaboration_bonus = 0.25 if is_collaboration else 0
            
            # Calculate total points
            total_multiplier = quality_multiplier * (1 + innovation_bonus) * viral_multiplier * (1 + collaboration_bonus)
            total_points = int(base_points * total_multiplier)
            
            # Award points
            unified_points_db.add_points(
                user_id,
                'clip_generation',
                total_points,
                source='clip_generation_activity'
            )
            
            # Activity points
            activity_points = int(total_points * 0.1)
            unified_points_db.add_points(
                user_id,
                'activity',
                activity_points,
                source='clip_generation_activity'
            )
            
            # Track generation
            if user_id not in self.generation_history:
                self.generation_history[user_id] = []
            
            generation_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'clip',
                'points_awarded': total_points,
                'clip_data': clip_data
            }
            self.generation_history[user_id].append(generation_entry)
            
            return {
                'success': True,
                'user_id': user_id,
                'base_points': base_points,
                'total_points': total_points,
                'activity_points': activity_points,
                'total_awarded': total_points + activity_points
            }
        except Exception as e:
            logger.error(f"Error awarding clip generation: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_generation_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user generation statistics"""
        history = self.generation_history.get(user_id, [])
        
        video_count = sum(1 for entry in history if entry['type'] == 'video')
        clip_count = sum(1 for entry in history if entry['type'] == 'clip')
        total_points = sum(entry['points_awarded'] for entry in history)
        
        return {
            'user_id': user_id,
            'total_generations': len(history),
            'video_count': video_count,
            'clip_count': clip_count,
            'total_points_earned': total_points,
            'average_points_per_generation': total_points / len(history) if history else 0,
            'recent_generations': history[-10:]
        }

video_generation_rewards = VideoGenerationRewards()
