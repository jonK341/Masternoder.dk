"""AI Editor Orchestrator - Coordinates different AI editors"""
import os
from typing import Dict, Any, Optional, List
from pathlib import Path


class EditorOrchestrator:
    """Orchestrates AI video editing using best available tools"""
    
    def __init__(self):
        """Initialize editor orchestrator"""
        self.ffmpeg_editor = None
        self.available_editors = []
        self._detect_available_editors()
    
    def _detect_available_editors(self):
        """Detect which editors are available"""
        # Check for FFmpeg (always available as fallback)
        if self._check_ffmpeg():
            from .ffmpeg_editor import FFmpegEditor
            self.ffmpeg_editor = FFmpegEditor()
            self.available_editors.append('ffmpeg')
            print("[Editor] FFmpeg detected and available")
        
        # TODO: Add other editor detections
        # - Stable Video Diffusion
        # - RunwayML API
        # - Pika Labs API
        # etc.
    
    def _check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        import shutil
        return shutil.which('ffmpeg') is not None
    
    def enhance_clip(
        self,
        clip_path: str,
        output_path: Optional[str] = None,
        enhancements: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Enhance a video clip with AI editing
        
        Args:
            clip_path: Path to input clip
            output_path: Path for output (if None, overwrites input)
            enhancements: Dict of enhancement options:
                - color_grading: bool
                - stabilization: bool
                - denoise: bool
                - upscale: bool
                - transitions: bool
        
        Returns:
            Path to enhanced clip, or None if failed
        """
        if not os.path.exists(clip_path):
            print(f"[Editor] Clip not found: {clip_path}")
            return None
        
        if not enhancements:
            enhancements = {
                'color_grading': True,
                'stabilization': False,
                'denoise': False,
                'upscale': False,
                'transitions': False
            }
        
        if not output_path:
            output_path = clip_path
        
        # Use FFmpeg as primary editor (most reliable, free, open source)
        if self.ffmpeg_editor:
            try:
                enhanced_path = self.ffmpeg_editor.enhance_clip(
                    clip_path,
                    output_path,
                    enhancements
                )
                if enhanced_path and os.path.exists(enhanced_path):
                    print(f"[Editor] Clip enhanced successfully: {enhanced_path}")
                    return enhanced_path
            except Exception as e:
                print(f"[Editor] FFmpeg enhancement failed: {e}")
        
        # Fallback: return original if enhancement fails
        print(f"[Editor] Enhancement failed, using original clip")
        return clip_path if os.path.exists(clip_path) else None
    
    def apply_color_grading(
        self,
        clip_path: str,
        theme: str = 'default',
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """Apply color grading based on theme
        
        Args:
            clip_path: Path to input clip
            theme: Theme name (matrix, cyberpunk, sci-fi, etc.)
            output_path: Path for output
        
        Returns:
            Path to graded clip
        """
        if not self.ffmpeg_editor:
            return clip_path
        
        return self.ffmpeg_editor.apply_color_grading(clip_path, theme, output_path)
    
    def add_transitions(
        self,
        clips: List[str],
        transition_type: str = 'fade',
        output_path: str = None
    ) -> Optional[str]:
        """Add transitions between clips
        
        Args:
            clips: List of clip paths
            transition_type: Type of transition (fade, dissolve, wipe, etc.)
            output_path: Path for output video
        
        Returns:
            Path to video with transitions
        """
        if not self.ffmpeg_editor:
            return None
        
        return self.ffmpeg_editor.add_transitions(clips, transition_type, output_path)
    
    def is_available(self) -> bool:
        """Check if any editor is available"""
        return len(self.available_editors) > 0
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of available editors"""
        return {
            'color_grading': self.ffmpeg_editor is not None,
            'stabilization': self.ffmpeg_editor is not None,
            'denoise': self.ffmpeg_editor is not None,
            'upscale': False,  # TODO: Add upscaling support
            'transitions': self.ffmpeg_editor is not None,
            'audio_mixing': self.ffmpeg_editor is not None,
        }

