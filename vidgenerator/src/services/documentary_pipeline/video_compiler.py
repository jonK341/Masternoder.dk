"""
Video Compiler - Compiles video clips into final documentary video
"""
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
import subprocess


class VideoCompiler:
    """Compiles video clips into final documentary"""
    
    def __init__(self):
        """Initialize video compiler"""
        self.ffmpeg_path = self._find_ffmpeg()
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable"""
        # Check common locations
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
    
    def compile_video(
        self,
        clip_paths: List[str],
        output_path: Path,
        transition_duration: float = 0.5,
        add_music: bool = False,
        music_path: Optional[str] = None,
        quality: str = 'medium',
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Compile video clips into final video
        
        Args:
            clip_paths: List of paths to video clip files
            output_path: Path for output video
            transition_duration: Duration of transitions between clips (seconds)
            add_music: Whether to add background music
            music_path: Path to music file (if add_music is True)
        
        Returns:
            True if successful, False otherwise
        """
        if not clip_paths:
            return False
        
        # If FFmpeg is not available, use moviepy as fallback
        if self.ffmpeg_path:
            return self._compile_with_ffmpeg(
                clip_paths, output_path, transition_duration, add_music, music_path, quality
            )
        else:
            return self._compile_with_moviepy(
                clip_paths, output_path, transition_duration, add_music, music_path, quality
            )
    
    def _compile_with_ffmpeg(
        self,
        clip_paths: List[str],
        output_path: Path,
        transition_duration: float,
        add_music: bool,
        music_path: Optional[str],
        quality: str = 'medium',
        ai_magi_overlay: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Compile using FFmpeg (more efficient)"""
        try:
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create file list for FFmpeg concat
            concat_file = output_path.parent / 'concat_list.txt'
            with open(concat_file, 'w') as f:
                for clip_path in clip_paths:
                    if os.path.exists(clip_path):
                        f.write(f"file '{os.path.abspath(clip_path)}'\n")
            
            # Quality settings
            quality_settings = {
                'low': {'crf': '28', 'preset': 'ultrafast', 'resolution': '854x480'},
                'medium': {'crf': '23', 'preset': 'medium', 'resolution': '1280x720'},
                'high': {'crf': '18', 'preset': 'slow', 'resolution': '1920x1080'}
            }
            q = quality_settings.get(quality.lower(), quality_settings['medium'])
            
            # Build FFmpeg command with quality settings
            if add_music and music_path and os.path.exists(music_path):
                # Use complex filter to add music
                cmd = [
                    self.ffmpeg_path,
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_file),
                    '-i', music_path,
                    '-c:v', 'libx264',
                    '-crf', q['crf'],
                    '-preset', q['preset'],
                    '-vf', f"scale={q['resolution']}",
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-shortest',  # End when shortest input ends
                    '-y',
                    str(output_path)
                ]
            else:
                # Build FFmpeg command with quality settings (no music)
                cmd = [
                    self.ffmpeg_path,
                    '-f', 'concat',
                    '-safe', '0',
                    '-i', str(concat_file),
                    '-c:v', 'libx264',
                    '-crf', q['crf'],
                    '-preset', q['preset'],
                    '-vf', f"scale={q['resolution']}",
                    '-c:a', 'aac',
                    '-b:a', '192k',
                    '-y',  # Overwrite output file
                    str(output_path)
                ]
            
            # Run FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300  # 5 minute timeout
            )
            
            # Clean up concat file
            if concat_file.exists():
                concat_file.unlink()
            
            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"[VideoCompiler] FFmpeg error: {result.stderr.decode('utf-8', errors='ignore')[:500]}")
                return False
                
        except Exception as e:
            print(f"[VideoCompiler] Error compiling with FFmpeg: {e}")
            return False
    
    def _compile_with_moviepy(
        self,
        clip_paths: List[str],
        output_path: Path,
        transition_duration: float,
        add_music: bool,
        music_path: Optional[str],
        quality: str = 'medium'
    ) -> bool:
        """Compile using MoviePy (fallback if FFmpeg not available)"""
        try:
            from moviepy.editor import VideoFileClip, concatenate_videoclips, CompositeVideoClip, AudioFileClip
            
            # Load video clips
            clips = []
            for clip_path in clip_paths:
                if os.path.exists(clip_path):
                    try:
                        clip = VideoFileClip(clip_path)
                        clips.append(clip)
                    except Exception as e:
                        print(f"[VideoCompiler] Error loading clip {clip_path}: {e}")
                        continue
            
            if not clips:
                return False
            
            # Concatenate clips
            final_clip = concatenate_videoclips(clips, method="compose")
            
            # Add music if requested
            if add_music and music_path and os.path.exists(music_path):
                try:
                    audio = AudioFileClip(music_path)
                    # Loop music if shorter than video
                    if audio.duration < final_clip.duration:
                        from moviepy.audio.AudioClip import concatenate_audioclips
                        loops_needed = int(final_clip.duration / audio.duration) + 1
                        audio = concatenate_audioclips([audio] * loops_needed)
                        audio = audio.subclip(0, final_clip.duration)
                    
                    final_clip = final_clip.set_audio(audio)
                except Exception as e:
                    print(f"[VideoCompiler] Error adding music: {e}")
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Quality settings
            quality_settings = {
                'low': {'bitrate': '500k', 'fps': 24, 'preset': 'ultrafast'},
                'medium': {'bitrate': '2000k', 'fps': 24, 'preset': 'medium'},
                'high': {'bitrate': '5000k', 'fps': 30, 'preset': 'slow'}
            }
            q = quality_settings.get(quality.lower(), quality_settings['medium'])
            
            # Write final video with quality settings
            final_clip.write_videofile(
                str(output_path),
                codec='libx264',
                audio_codec='aac',
                fps=q['fps'],
                preset=q['preset'],
                bitrate=q['bitrate']
            )
            
            # Clean up
            final_clip.close()
            for clip in clips:
                clip.close()
            
            return True
            
        except ImportError:
            print("[VideoCompiler] MoviePy not available, cannot compile video")
            return False
        except Exception as e:
            print(f"[VideoCompiler] Error compiling with MoviePy: {e}")
            return False
    
    def create_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: float = 1.0,
        quality: str = 'high',
        width: int = 1280,
        height: int = 720
    ) -> bool:
        """
        Create thumbnail from video with enhanced quality settings
        
        Args:
            video_path: Path to video file
            output_path: Path for thumbnail image
            timestamp: Time in video to capture (seconds)
            quality: Quality setting ('low', 'medium', 'high') - affects compression
            width: Thumbnail width in pixels (default: 1280)
            height: Thumbnail height in pixels (default: 720)
        
        Returns:
            True if successful
        """
        if self.ffmpeg_path:
            try:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Quality settings for JPEG compression
                quality_settings = {
                    'low': {'q': '5', 'qscale': '5'},      # Lower quality, smaller file
                    'medium': {'q': '3', 'qscale': '3'},   # Balanced
                    'high': {'q': '2', 'qscale': '2'}      # Higher quality
                }
                q = quality_settings.get(quality.lower(), quality_settings['high'])
                
                # Get video duration to ensure timestamp is valid
                probe_cmd = [
                    self.ffmpeg_path,
                    '-i', str(video_path),
                    '-show_entries', 'format=duration',
                    '-v', 'quiet',
                    '-of', 'csv=p=0'
                ]
                probe_result = subprocess.run(
                    probe_cmd,
                    capture_output=True,
                    timeout=10
                )
                
                if probe_result.returncode == 0:
                    try:
                        duration = float(probe_result.stdout.decode().strip())
                        # Use middle of video if timestamp is too early or too late
                        if timestamp < 0.5 or timestamp > duration - 0.5:
                            timestamp = max(1.0, min(timestamp, duration / 2))
                    except (ValueError, AttributeError):
                        pass  # Use provided timestamp if can't get duration
                
                # Build enhanced FFmpeg command for high-quality thumbnail
                cmd = [
                    self.ffmpeg_path,
                    '-i', str(video_path),
                    '-ss', str(timestamp),
                    '-vframes', '1',
                    '-vf', f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',  # Scale and pad to maintain aspect ratio
                    '-qscale:v', q['qscale'],  # JPEG quality (lower = better)
                    '-y',
                    str(output_path)
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    timeout=30
                )
                
                return result.returncode == 0 and output_path.exists()
                
            except Exception as e:
                print(f"[VideoCompiler] Error creating thumbnail with FFmpeg: {e}")
                return False
        else:
            # Fallback to moviepy
            try:
                from moviepy.editor import VideoFileClip
                from PIL import Image
                
                clip = VideoFileClip(str(video_path))
                frame = clip.get_frame(timestamp)
                
                img = Image.fromarray(frame)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                img.save(output_path)
                
                clip.close()
                return True
                
            except Exception as e:
                print(f"[VideoCompiler] Error creating thumbnail: {e}")
                return False

