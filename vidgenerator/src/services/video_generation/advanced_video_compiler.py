"""
Advanced Video Compiler - Professional video editing pipeline
Includes transitions, color grading, stabilization, and audio enhancement
"""
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum


class TransitionType(Enum):
    """Video transition types"""
    CROSSFADE = "crossfade"
    WIPE = "wipe"
    ZOOM = "zoom"
    FADE_BLACK = "fade_black"
    NONE = "none"


class AdvancedVideoCompiler:
    """Advanced video compiler with professional features"""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize advanced video compiler
        
        Args:
            ffmpeg_path: Path to FFmpeg executable
        """
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable"""
        possible_paths = [
            'ffmpeg',
            '/usr/bin/ffmpeg',
            '/usr/local/bin/ffmpeg',
            'C:\\ffmpeg\\bin\\ffmpeg.exe'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    return path
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        
        return None
    
    def compile_with_transitions(
        self,
        clip_paths: List[str],
        output_path: Path,
        transition_type: TransitionType = TransitionType.CROSSFADE,
        transition_duration: float = 0.5,
        quality_settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Compile video clips with professional transitions
        
        Args:
            clip_paths: List of clip file paths
            output_path: Output video path
            transition_type: Type of transition
            transition_duration: Transition duration in seconds
            quality_settings: Quality settings dictionary
        
        Returns:
            True if successful
        """
        if not clip_paths:
            return False
        
        if not self.ffmpeg_path:
            # Fallback to basic compilation
            return self._compile_basic(clip_paths, output_path, quality_settings)
        
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Build complex filter for transitions
            filter_complex = self._build_transition_filter(
                clip_paths,
                transition_type,
                transition_duration
            )
            
            # Get quality settings
            if not quality_settings:
                quality_settings = {
                    'crf': '23',
                    'preset': 'medium',
                    'resolution': '1920x1080',
                    'fps': '24'
                }
            
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                '-y'
            ]
            
            # Add input files
            for clip_path in clip_paths:
                if os.path.exists(clip_path):
                    cmd.extend(['-i', clip_path])
            
            # Add complex filter
            if filter_complex:
                cmd.extend(['-filter_complex', filter_complex])
            
            # Add encoding settings
            cmd.extend([
                '-c:v', 'libx264',
                '-crf', str(quality_settings.get('crf', '23')),
                '-preset', quality_settings.get('preset', 'medium'),
                '-vf', f"scale={quality_settings.get('resolution', '1920x1080')}",
                '-r', str(quality_settings.get('fps', '24')),
                '-c:a', 'aac',
                '-b:a', quality_settings.get('audio_bitrate', '192k'),
                '-shortest',
                str(output_path)
            ])
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600,  # 10 minute timeout
                text=True
            )
            
            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"[AdvancedCompiler] FFmpeg error: {result.stderr[:500]}")
                return False
                
        except Exception as e:
            print(f"[AdvancedCompiler] Error: {e}")
            return False
    
    def _build_transition_filter(
        self,
        clip_paths: List[str],
        transition_type: TransitionType,
        duration: float
    ) -> Optional[str]:
        """Build FFmpeg filter_complex for transitions"""
        if transition_type == TransitionType.NONE:
            return None
        
        if transition_type == TransitionType.CROSSFADE:
            # Crossfade transition
            filter_parts = []
            num_clips = len(clip_paths)
            
            for i in range(num_clips):
                if i == 0:
                    # First clip: fade out
                    filter_parts.append(
                        f"[0:v]fade=t=out:st={self._get_clip_duration(clip_paths[0]) - duration}:d={duration}[v0]"
                    )
                elif i == num_clips - 1:
                    # Last clip: fade in
                    filter_parts.append(
                        f"[{i}:v]fade=t=in:st=0:d={duration}[v{i}]"
                    )
                else:
                    # Middle clips: fade in and out
                    clip_dur = self._get_clip_duration(clip_paths[i])
                    filter_parts.append(
                        f"[{i}:v]fade=t=in:st=0:d={duration},fade=t=out:st={clip_dur - duration}:d={duration}[v{i}]"
                    )
            
            # Concatenate with crossfade
            concat_inputs = ''.join([f"[v{i}]" for i in range(num_clips)])
            filter_parts.append(f"{concat_inputs}concat=n={num_clips}:v=1:a=0[outv]")
            
            return ';'.join(filter_parts)
        
        elif transition_type == TransitionType.FADE_BLACK:
            # Fade to black between clips
            filter_parts = []
            for i in range(len(clip_paths)):
                clip_dur = self._get_clip_duration(clip_paths[i])
                filter_parts.append(
                    f"[{i}:v]fade=t=in:st=0:d={duration},fade=t=out:st={clip_dur - duration}:d={duration}[v{i}]"
                )
            
            concat_inputs = ''.join([f"[v{i}]" for i in range(len(clip_paths))])
            filter_parts.append(f"{concat_inputs}concat=n={len(clip_paths)}:v=1:a=0[outv]")
            
            return ';'.join(filter_parts)
        
        # For other transitions, use crossfade as default
        return self._build_transition_filter(clip_paths, TransitionType.CROSSFADE, duration)
    
    def _get_clip_duration(self, clip_path: str) -> float:
        """Get clip duration in seconds"""
        if not self.ffmpeg_path or not os.path.exists(clip_path):
            return 5.0  # Default
        
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', clip_path,
                '-show_entries', 'format=duration',
                '-v', 'quiet',
                '-of', 'csv=p=0'
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=10, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except Exception:
            pass
        
        return 5.0  # Default
    
    def apply_color_grading(
        self,
        video_path: Path,
        style: str = 'standard',
        output_path: Optional[Path] = None
    ) -> bool:
        """
        Apply color grading to video
        
        Args:
            video_path: Input video path
            style: Color grading style (standard, cinematic, vibrant, muted)
            output_path: Output path (overwrites input if None)
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Color grading filters based on style
            color_filters = {
                'standard': 'eq=contrast=1.1:brightness=0.02:saturation=1.05',
                'cinematic': 'eq=contrast=1.2:brightness=-0.05:saturation=0.9:gamma=1.1',
                'vibrant': 'eq=contrast=1.15:brightness=0.05:saturation=1.2',
                'muted': 'eq=contrast=1.0:brightness=0.0:saturation=0.85'
            }
            
            filter_str = color_filters.get(style.lower(), color_filters['standard'])
            
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', filter_str,
                '-c:v', 'libx264',
                '-crf', '18',  # High quality
                '-preset', 'slow',
                '-c:a', 'copy',  # Copy audio
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,
                text=True
            )
            
            return result.returncode == 0 and output_path.exists()
            
        except Exception as e:
            print(f"[AdvancedCompiler] Color grading error: {e}")
            return False
    
    def stabilize_video(self, video_path: Path, output_path: Optional[Path] = None) -> bool:
        """
        Stabilize video to reduce shakiness
        
        Args:
            video_path: Input video path
            output_path: Output path (overwrites input if None)
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Two-pass stabilization
            # Pass 1: Analyze
            analyze_path = output_path.parent / f"{output_path.stem}_analyze.trf"
            
            cmd1 = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', 'vidstabdetect=shakiness=5:accuracy=15:result=' + str(analyze_path),
                '-f', 'null',
                '-'
            ]
            
            result1 = subprocess.run(cmd1, capture_output=True, timeout=300)
            
            if result1.returncode != 0:
                return False
            
            # Pass 2: Transform
            cmd2 = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', f'vidstabtransform=input={analyze_path}:zoom=1:smoothing=10',
                '-c:v', 'libx264',
                '-preset', 'medium',
                '-c:a', 'copy',
                '-y',
                str(output_path)
            ]
            
            result2 = subprocess.run(cmd2, capture_output=True, timeout=300)
            
            # Clean up
            if analyze_path.exists():
                analyze_path.unlink()
            
            return result2.returncode == 0 and output_path.exists()
            
        except Exception as e:
            print(f"[AdvancedCompiler] Stabilization error: {e}")
            return False
    
    def enhance_audio(
        self,
        video_path: Path,
        music_path: Optional[str] = None,
        music_volume: float = 0.3,
        output_path: Optional[Path] = None
    ) -> bool:
        """
        Enhance audio with background music and processing
        
        Args:
            video_path: Input video path
            music_path: Optional background music path
            music_volume: Music volume (0.0 - 1.0)
            output_path: Output path
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            if music_path and os.path.exists(music_path):
                # Mix video audio with background music
                filter_complex = (
                    f"[0:a]volume=1.0[a0];"
                    f"[1:a]volume={music_volume}[a1];"
                    f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                )
                
                cmd = [
                    self.ffmpeg_path,
                    '-i', str(video_path),
                    '-i', music_path,
                    '-filter_complex', filter_complex,
                    '-map', '0:v',
                    '-map', '[aout]',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-y',
                    str(output_path)
                ]
            else:
                # Just enhance existing audio
                cmd = [
                    self.ffmpeg_path,
                    '-i', str(video_path),
                    '-af', 'highpass=f=80,lowpass=f=12000,volume=1.1',
                    '-c:v', 'copy',
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-y',
                    str(output_path)
                ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,
                text=True
            )
            
            return result.returncode == 0 and output_path.exists()
            
        except Exception as e:
            print(f"[AdvancedCompiler] Audio enhancement error: {e}")
            return False
    
    def _compile_basic(
        self,
        clip_paths: List[str],
        output_path: Path,
        quality_settings: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Basic compilation fallback"""
        try:
            from src.services.documentary_pipeline.video_compiler import VideoCompiler
            compiler = VideoCompiler()
            return compiler.compile_video(
                clip_paths=clip_paths,
                output_path=output_path,
                quality=quality_settings.get('quality', 'medium') if quality_settings else 'medium'
            )
        except Exception:
            return False

