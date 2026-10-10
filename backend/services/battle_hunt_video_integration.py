"""
Battle & Hunt Video Integration Service
Combines video generation with battle results and hunt achievements
"""
import os
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict

class BattleHuntVideoIntegration:
    """Integrates video generation with battle and hunt systems"""
    
    def __init__(self):
        self.battle_videos = {}  # {battle_id: video_data}
        self.hunt_videos = {}  # {hunt_id: video_data}
        self.user_video_history = defaultdict(list)  # {user_id: [video_data]}
        
    def generate_battle_video(
        self,
        battle_id: str,
        user_id: str,
        battle_result: Dict[str, Any],
        video_style: str = "epic",
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a video from battle results
        
        Args:
            battle_id: ID of the battle
            user_id: User who initiated the video generation
            battle_result: Battle result data (winner, scores, rewards, etc.)
            video_style: Style of video (epic, cinematic, action, documentary)
            quality: Video quality (low, medium, high)
        
        Returns:
            Video generation result with battle context
        """
        try:
            # Extract battle information
            winner = battle_result.get('winner')
            clan1_name = battle_result.get('clan1_name', 'Clan 1')
            clan2_name = battle_result.get('clan2_name', 'Clan 2')
            clan1_score = battle_result.get('clan1_score', 0)
            clan2_score = battle_result.get('clan2_score', 0)
            battle_type = battle_result.get('battle_type', 'standard')
            rewards = battle_result.get('rewards', {})
            
            # Generate video prompt based on battle result
            if winner == 'clan1':
                prompt = f"Epic battle victory: {clan1_name} defeats {clan2_name} in a fierce {battle_type} battle. Final score: {clan1_score} to {clan2_score}. Celebrating warriors, victory banners, and triumphant moments."
            elif winner == 'clan2':
                prompt = f"Epic battle victory: {clan2_name} defeats {clan1_name} in a fierce {battle_type} battle. Final score: {clan2_score} to {clan1_score}. Celebrating warriors, victory banners, and triumphant moments."
            else:
                prompt = f"Intense battle between {clan1_name} and {clan2_name} ends in a draw. Score: {clan1_score} to {clan2_score}. Both clans showing respect and honor."
            
            # Add style-specific enhancements
            style_prompts = {
                "epic": "Cinematic epic battle scene with dramatic lighting, slow motion, and heroic poses.",
                "cinematic": "Film-quality battle documentary with professional cinematography and dramatic angles.",
                "action": "Fast-paced action sequence with dynamic camera movements and intense combat scenes.",
                "documentary": "Documentary-style narration of the battle with historical context and analysis."
            }
            
            enhanced_prompt = f"{prompt} {style_prompts.get(video_style, style_prompts['epic'])}"
            
            # Create video title
            video_title = f"Battle: {clan1_name} vs {clan2_name}"
            if winner:
                winner_name = clan1_name if winner == 'clan1' else clan2_name
                video_title = f"{winner_name} Victory - {video_title}"
            
            # Generate video using PipelineOrchestrator
            video_result = self._generate_video(
                user_id=user_id,
                title=video_title,
                prompt=enhanced_prompt,
                quality=quality,
                category="battle",
                metadata={
                    "battle_id": battle_id,
                    "battle_type": battle_type,
                    "clan1_name": clan1_name,
                    "clan2_name": clan2_name,
                    "clan1_score": clan1_score,
                    "clan2_score": clan2_score,
                    "winner": winner,
                    "rewards": rewards,
                    "video_style": video_style,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Store battle video reference
            self.battle_videos[battle_id] = {
                "video_id": video_result.get('doc_id'),
                "user_id": user_id,
                "battle_id": battle_id,
                "created_at": datetime.utcnow().isoformat(),
                "status": video_result.get('status', 'processing')
            }
            
            # Track in user history
            self.user_video_history[user_id].append({
                "type": "battle",
                "battle_id": battle_id,
                "video_id": video_result.get('doc_id'),
                "created_at": datetime.utcnow().isoformat()
            })
            
            return {
                "success": True,
                "video_result": video_result,
                "battle_context": {
                    "battle_id": battle_id,
                    "clan1_name": clan1_name,
                    "clan2_name": clan2_name,
                    "winner": winner,
                    "scores": {"clan1": clan1_score, "clan2": clan2_score}
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "battle_id": battle_id
            }
    
    def generate_hunt_video(
        self,
        user_id: str,
        hunt_event: Dict[str, Any],
        video_style: str = "adventure",
        quality: str = "medium"
    ) -> Dict[str, Any]:
        """
        Generate a video from hunt/trophy achievement
        
        Args:
            user_id: User who achieved the hunt/trophy
            hunt_event: Hunt event data (achievement, trophy, level_up, etc.)
            video_style: Style of video (adventure, documentary, cinematic, celebration)
            quality: Video quality (low, medium, high)
        
        Returns:
            Video generation result with hunt context
        """
        try:
            event_type = hunt_event.get('type', 'achievement')  # achievement, trophy, level_up, milestone
            event_name = hunt_event.get('name', 'Hunt Achievement')
            description = hunt_event.get('description', '')
            level = hunt_event.get('level', 0)
            xp_gained = hunt_event.get('xp_gained', 0)
            trophies = hunt_event.get('trophies', [])
            
            # Generate video prompt based on event type
            if event_type == 'level_up':
                prompt = f"Epic level up celebration: Hunter reaches level {level}! Gaining {xp_gained} XP. Unlocking new abilities, power surges, and heroic transformation. Adventure and achievement."
            elif event_type == 'trophy':
                trophy_names = ", ".join([t.get('name', 'Trophy') for t in trophies[:3]])
                prompt = f"Trophy hunt success: Hunter collects {trophy_names}. Epic trophy collection moment with golden trophies, celebration, and achievement recognition."
            elif event_type == 'milestone':
                prompt = f"Major milestone achieved: {event_name}. {description}. Epic milestone celebration with fireworks, achievements, and progress visualization."
            else:
                prompt = f"Hunt achievement unlocked: {event_name}. {description}. Adventure and discovery moment with exploration and success."
            
            # Add style-specific enhancements
            style_prompts = {
                "adventure": "Adventure documentary style with exploration, discovery, and epic landscapes.",
                "documentary": "Professional documentary narration with detailed analysis and storytelling.",
                "cinematic": "Cinematic celebration with dramatic lighting, slow motion, and epic visuals.",
                "celebration": "Joyful celebration with confetti, fireworks, and triumphant moments."
            }
            
            enhanced_prompt = f"{prompt} {style_prompts.get(video_style, style_prompts['adventure'])}"
            
            # Create video title
            video_title = f"Hunt: {event_name}"
            if event_type == 'level_up':
                video_title = f"Level {level} Achievement"
            elif event_type == 'trophy':
                video_title = f"Trophy Collection: {trophy_names}"
            
            # Generate video
            hunt_id = f"hunt_{uuid.uuid4().hex[:8]}"
            video_result = self._generate_video(
                user_id=user_id,
                title=video_title,
                prompt=enhanced_prompt,
                quality=quality,
                category="hunt",
                metadata={
                    "hunt_id": hunt_id,
                    "event_type": event_type,
                    "event_name": event_name,
                    "level": level,
                    "xp_gained": xp_gained,
                    "trophies": trophies,
                    "video_style": video_style,
                    "generated_at": datetime.utcnow().isoformat()
                }
            )
            
            # Store hunt video reference
            self.hunt_videos[hunt_id] = {
                "video_id": video_result.get('doc_id'),
                "user_id": user_id,
                "hunt_id": hunt_id,
                "event_type": event_type,
                "created_at": datetime.utcnow().isoformat(),
                "status": video_result.get('status', 'processing')
            }
            
            # Track in user history
            self.user_video_history[user_id].append({
                "type": "hunt",
                "hunt_id": hunt_id,
                "video_id": video_result.get('doc_id'),
                "event_type": event_type,
                "created_at": datetime.utcnow().isoformat()
            })
            
            return {
                "success": True,
                "video_result": video_result,
                "hunt_context": {
                    "hunt_id": hunt_id,
                    "event_type": event_type,
                    "event_name": event_name,
                    "level": level,
                    "xp_gained": xp_gained
                }
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "user_id": user_id
            }
    
    def _generate_video(
        self,
        user_id: str,
        title: str,
        prompt: str,
        quality: str = "medium",
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Internal method to generate video using PipelineOrchestrator
        
        Args:
            user_id: User ID
            title: Video title
            prompt: Video generation prompt
            quality: Video quality
            category: Video category
            metadata: Additional metadata
        
        Returns:
            Video generation result
        """
        try:
            from src.services.documentary_pipeline.pipeline_orchestrator import PipelineOrchestrator
            from flask import current_app
            
            # Get app context
            app = current_app._get_current_object()
            
            # Create orchestrator
            with app.app_context():
                orchestrator = PipelineOrchestrator()
                
                # Generate unique document ID
                doc_id = f"battle_hunt_{uuid.uuid4().hex[:12]}"
                
                # Generate video
                result = orchestrator.generate_documentary(
                    doc_id=doc_id,
                    prompt=prompt,
                    title=title,
                    description=prompt,
                    attributes={
                        "quality": quality,
                        "category": category,
                        "user_id": user_id,
                        "metadata": metadata or {}
                    }
                )
                
                return {
                    "doc_id": doc_id,
                    "status": "processing",
                    "title": title,
                    "prompt": prompt,
                    "quality": quality,
                    "category": category,
                    "result": result
                }
                
        except Exception as e:
            # Fallback: return placeholder result
            return {
                "doc_id": f"battle_hunt_{uuid.uuid4().hex[:12]}",
                "status": "error",
                "error": str(e),
                "title": title,
                "prompt": prompt
            }
    
    def get_battle_video(self, battle_id: str) -> Optional[Dict[str, Any]]:
        """Get video data for a battle"""
        return self.battle_videos.get(battle_id)
    
    def get_hunt_video(self, hunt_id: str) -> Optional[Dict[str, Any]]:
        """Get video data for a hunt event"""
        return self.hunt_videos.get(hunt_id)
    
    def get_user_video_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get user's battle/hunt video history"""
        history = self.user_video_history.get(user_id, [])
        return sorted(history, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]
    
    def get_all_battle_videos(self) -> Dict[str, Dict[str, Any]]:
        """Get all battle videos"""
        return self.battle_videos
    
    def get_all_hunt_videos(self) -> Dict[str, Dict[str, Any]]:
        """Get all hunt videos"""
        return self.hunt_videos


# Global instance
battle_hunt_video_integration = BattleHuntVideoIntegration()

