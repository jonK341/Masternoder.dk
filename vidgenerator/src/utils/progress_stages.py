"""
Progress stages for video generation with detailed stage information
"""
from typing import Dict, List
from enum import Enum


class ProgressStage(Enum):
    """Enumeration of video generation stages"""
    INITIALIZING = ("initializing", "Initialiserer...", 0, 5)
    SCRIPT_GENERATION = ("script_generation", "Genererer script og indhold...", 5, 20)
    SCRIPT_COMPLETE = ("script_complete", "Script genereret", 20, 25)
    CLIP_GENERATION_START = ("clip_generation_start", "Starter video klip generering...", 25, 30)
    CLIP_GENERATION = ("clip_generation", "Genererer video klip...", 30, 80)
    VIDEO_COMPILATION = ("video_compilation", "Kompilerer video klip...", 80, 90)
    COMPILATION_COMPLETE = ("compilation_complete", "Video kompilation færdig", 90, 93)
    THUMBNAIL_GENERATION = ("thumbnail_generation", "Genererer thumbnail...", 93, 98)
    FINALIZING = ("finalizing", "Færdiggør video...", 98, 100)
    GENERATION_COMPLETE = ("generation_complete", "Generering færdig!", 100, 100)
    ERROR = ("error", "Fejl opstod", 0, 0)
    FALLBACK = ("fallback", "Bruger fallback metode...", 0, 0)


class ProgressStageManager:
    """Manages progress stages with detailed information"""
    
    # Stage descriptions in Danish
    STAGE_DESCRIPTIONS = {
        "initializing": "Initialiserer video generering...",
        "script_generation": "Genererer script og indhold med AI...",
        "script_complete": "Script genereret. Klar til klip generering.",
        "clip_generation_start": "Starter video klip generering...",
        "clip_generation": "Genererer video klip med AI...",
        "video_compilation": "Kompilerer video klip til final video...",
        "compilation_complete": "Video kompilation færdig.",
        "thumbnail_generation": "Genererer thumbnail billede...",
        "finalizing": "Færdiggør video og opdaterer database...",
        "generation_complete": "Generering færdig! Video klar.",
        "error": "Fejl opstod under generering.",
        "fallback": "Bruger fallback metode (ingen klip genereret)."
    }
    
    @staticmethod
    def get_stage_info(stage_key: str) -> Dict[str, any]:
        """Get detailed information about a progress stage"""
        stage = None
        for s in ProgressStage:
            if s.value[0] == stage_key:
                stage = s
                break
        
        if not stage:
            return {
                'key': stage_key,
                'message': stage_key,
                'min_progress': 0,
                'max_progress': 100,
                'description': ProgressStageManager.STAGE_DESCRIPTIONS.get(stage_key, stage_key)
            }
        
        return {
            'key': stage.value[0],
            'message': stage.value[1],
            'min_progress': stage.value[2],
            'max_progress': stage.value[3],
            'description': ProgressStageManager.STAGE_DESCRIPTIONS.get(stage.value[0], stage.value[1])
        }
    
    @staticmethod
    def calculate_progress(
        stage_key: str,
        substage_progress: float = 0.0,
        current_item: int = 0,
        total_items: int = 1
    ) -> int:
        """
        Calculate overall progress percentage based on stage and substage
        
        Args:
            stage_key: Current stage key
            substage_progress: Progress within current stage (0.0 to 1.0)
            current_item: Current item number (for multi-item stages)
            total_items: Total number of items
        
        Returns:
            Overall progress percentage (0-100)
        """
        stage_info = ProgressStageManager.get_stage_info(stage_key)
        min_progress = stage_info['min_progress']
        max_progress = stage_info['max_progress']
        stage_range = max_progress - min_progress
        
        # For multi-item stages (like clip generation), calculate item-based progress
        if stage_key == "clip_generation" and total_items > 1:
            item_progress = current_item / total_items
            stage_progress = item_progress + (substage_progress / total_items)
        else:
            stage_progress = substage_progress
        
        # Calculate overall progress
        overall_progress = min_progress + (stage_range * stage_progress)
        
        return int(overall_progress)
    
    @staticmethod
    def get_user_friendly_message(stage_key: str, **kwargs) -> str:
        """
        Get user-friendly message for a stage
        
        Args:
            stage_key: Stage key
            **kwargs: Additional context (clip_num, total_clips, etc.)
        
        Returns:
            User-friendly message string
        """
        base_message = ProgressStageManager.STAGE_DESCRIPTIONS.get(
            stage_key,
            stage_key.replace('_', ' ').title()
        )
        
        # Add context for specific stages
        if stage_key == "clip_generation" and 'clip_num' in kwargs and 'total_clips' in kwargs:
            clip_num = kwargs.get('clip_num', 0)
            total_clips = kwargs.get('total_clips', 1)
            return f"Genererer video klip {clip_num}/{total_clips}..."
        
        return base_message


def get_progress_message_map() -> Dict[str, str]:
    """Get mapping of progress keys to user-friendly Danish messages"""
    return ProgressStageManager.STAGE_DESCRIPTIONS.copy()


