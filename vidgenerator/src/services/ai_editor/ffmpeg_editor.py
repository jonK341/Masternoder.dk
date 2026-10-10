"""FFmpeg-based video editor - Free, open source video editing"""
import os
import subprocess
from typing import Dict, Any, Optional, List
from pathlib import Path
import tempfile


class FFmpegEditor:
    """FFmpeg-based video editor for free video enhancement"""
    
    def __init__(self):
        """Initialize FFmpeg editor"""
        self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable"""
        import shutil
        ffmpeg = shutil.which('ffmpeg')
        if not ffmpeg:
            # Try common paths
            common_paths = [
                '/usr/bin/ffmpeg',
                '/usr/local/bin/ffmpeg',
                'C:\\ffmpeg\\bin\\ffmpeg.exe',
                os.path.join(os.path.dirname(__file__), '..', '..', '..', 'ffmpeg', 'bin', 'ffmpeg.exe')
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        return ffmpeg
    
    def enhance_clip(
        self,
        clip_path: str,
        output_path: Optional[str] = None,
        enhancements: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Enhance video clip with various improvements
        
        Args:
            clip_path: Input clip path
            output_path: Output path (if None, overwrites input)
            enhancements: Enhancement options
        
        Returns:
            Path to enhanced clip
        """
        if not self.ffmpeg_path:
            print("[FFmpegEditor] FFmpeg not found, skipping enhancement")
            return clip_path
        
        if not os.path.exists(clip_path):
            print(f"[FFmpegEditor] Clip not found: {clip_path}")
            return None
        
        if not output_path:
            output_path = clip_path
        
        if not enhancements:
            enhancements = {}
        
        try:
            # Build FFmpeg command with enhancements
            cmd = [self.ffmpeg_path, '-i', clip_path]
            
            # Color grading (subtle enhancement)
            if enhancements.get('color_grading', True):
                # Apply subtle color enhancement
                cmd.extend([
                    '-vf', 'eq=contrast=1.1:brightness=0.02:saturation=1.05'
                ])
            
            # Denoise
            if enhancements.get('denoise', False):
                cmd.extend([
                    '-vf', 'hqdn3d=4:3:6:4.5'
                ])
            
            # Stabilization (if enabled, requires two-pass)
            if enhancements.get('stabilization', False):
                # This is complex, skip for now or implement separately
                pass
            
            # Output settings
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',  # Good quality/size balance
                '-c:a', 'copy',  # Keep original audio
                '-y',  # Overwrite output
                output_path
            ])
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"[FFmpegEditor] Enhanced clip saved: {output_path}")
                return output_path
            else:
                print(f"[FFmpegEditor] FFmpeg failed: {result.stderr.decode()}")
                return clip_path  # Return original on failure
                
        except subprocess.TimeoutExpired:
            print("[FFmpegEditor] FFmpeg timeout, using original clip")
            return clip_path
        except Exception as e:
            print(f"[FFmpegEditor] Error enhancing clip: {e}")
            return clip_path
    
    def apply_color_grading(
        self,
        clip_path: str,
        theme: str = 'default',
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """Apply theme-based color grading
        
        Args:
            clip_path: Input clip
            theme: Theme name (matrix, cyberpunk, sci-fi, etc.)
            output_path: Output path
        
        Returns:
            Path to graded clip
        """
        if not self.ffmpeg_path:
            return clip_path
        
        if not output_path:
            output_path = clip_path
        
        # Theme-based color grading filters
        theme_filters = {
            'matrix': 'eq=contrast=1.2:brightness=-0.1:saturation=0.8:gamma=1.1,curves=all="0/0 0.5/0.4 1/1"',
            'cyberpunk': 'eq=contrast=1.3:brightness=0.05:saturation=1.2,curves=green="0/0 0.5/0.6 1/1":blue="0/0 0.5/0.7 1/1"',
            'sci-fi': 'eq=contrast=1.15:brightness=0.03:saturation=1.1,curves=all="0/0 0.5/0.5 1/1"',
            'nature': 'eq=contrast=1.05:brightness=0.02:saturation=1.15,curves=green="0/0 0.5/0.55 1/1"',
            'default': 'eq=contrast=1.1:brightness=0.02:saturation=1.05'
        }
        
        filter_complex = theme_filters.get(theme.lower(), theme_filters['default'])
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', clip_path,
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'copy',
                '-y',
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300
            )
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"[FFmpegEditor] Color grading applied ({theme}): {output_path}")
                return output_path
            else:
                return clip_path
                
        except Exception as e:
            print(f"[FFmpegEditor] Color grading error: {e}")
            return clip_path
    
    def add_transitions(
        self,
        clips: List[str],
        transition_type: str = 'fade',
        output_path: str = None
    ) -> Optional[str]:
        """Add transitions between clips
        
        Args:
            clips: List of clip paths
            transition_type: Transition type (fade, dissolve, wipe)
            output_path: Output path
        
        Returns:
            Path to video with transitions
        """
        if not self.ffmpeg_path or len(clips) < 2:
            return None
        
        if not output_path:
            output_path = tempfile.mktemp(suffix='.mp4')
        
        try:
            # Create concat file for FFmpeg
            concat_file = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False)
            for clip in clips:
                concat_file.write(f"file '{os.path.abspath(clip)}'\n")
            concat_file.close()
            
            # Build filter for transitions
            if transition_type == 'fade':
                # Simple fade in/out between clips
                filter_complex = self._build_fade_filter(len(clips))
            else:
                filter_complex = None
            
            cmd = [
                self.ffmpeg_path,
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file.name,
            ]
            
            if filter_complex:
                cmd.extend(['-filter_complex', filter_complex])
            
            cmd.extend([
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-crf', '23',
                '-c:a', 'copy',
                '-y',
                output_path
            ])
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=600  # 10 minute timeout for multiple clips
            )
            
            # Clean up
            os.unlink(concat_file.name)
            
            if result.returncode == 0 and os.path.exists(output_path):
                print(f"[FFmpegEditor] Transitions added: {output_path}")
                return output_path
            else:
                print(f"[FFmpegEditor] Transition failed: {result.stderr.decode()}")
                return None
                
        except Exception as e:
            print(f"[FFmpegEditor] Transition error: {e}")
            return None
    
    def _build_fade_filter(self, clip_count: int) -> str:
        """Build fade filter complex for multiple clips"""
        # Simple fade in/out - for now just fade in first and fade out last
        # More complex transitions would require xfade filter
        return f"fade=t=in:st=0:d=0.5,fade=t=out:st={max(0, 1)}:d=0.5"

