"""
Subtitle Embedder - Embeds subtitles into videos using FFmpeg
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from .subtitle_generator import SubtitleGenerator


class SubtitleEmbedder:
    """Embed subtitles into video files"""
    
    def __init__(self):
        self.subtitle_generator = SubtitleGenerator()
    
    def embed_subtitles(
        self,
        video_path: str,
        subtitle_data: Optional[Dict[str, Any]] = None,
        subtitle_file: Optional[str] = None,
        output_path: Optional[str] = None,
        style: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Embed subtitles into video file
        
        Args:
            video_path: Path to input video file
            subtitle_data: Subtitle data dictionary (will be converted to SRT)
            subtitle_file: Path to existing SRT file
            output_path: Path for output video (if None, overwrites input)
            style: Subtitle styling options
        
        Returns:
            Result dictionary with success status and output path
        """
        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            return {
                'success': False,
                'error': f'Video file not found: {video_path}'
            }
        
        # Determine output path
        if output_path is None:
            output_path = str(video_path_obj.with_suffix('.with_subs.mp4'))
        else:
            output_path = str(Path(output_path))
        
        # Get or create subtitle file
        srt_file = subtitle_file
        if srt_file is None and subtitle_data:
            # Create temporary SRT file
            srt_file = str(video_path_obj.with_suffix('.srt'))
            if not self.subtitle_generator.save_subtitles(subtitle_data, srt_file):
                return {
                    'success': False,
                    'error': 'Failed to create subtitle file'
                }
        
        if not srt_file or not Path(srt_file).exists():
            return {
                'success': False,
                'error': f'Subtitle file not found: {srt_file}'
            }
        
        # Default subtitle style
        if style is None:
            style = {
                'fontsize': 24,
                'fontcolor': 'white',
                'outlinecolor': 'black',
                'outline': 2,
                'alignment': 2,  # Bottom center
                'marginv': 30
            }
        
        # Build FFmpeg command for subtitle embedding
        # Using subtitles filter for hardcoded subtitles
        ffmpeg_cmd = [
            'ffmpeg',
            '-i', str(video_path),
            '-vf', self._build_subtitle_filter(srt_file, style),
            '-c:a', 'copy',  # Copy audio without re-encoding
            '-c:v', 'libx264',
            '-preset', 'medium',
            '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-movflags', '+faststart',
            '-y',  # Overwrite output file
            output_path
        ]
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'FFmpeg error: {result.stderr[:500]}'
                }
            
            if not Path(output_path).exists():
                return {
                    'success': False,
                    'error': 'Output file was not created'
                }
            
            # Clean up temporary SRT file if we created it
            if subtitle_data and Path(srt_file).exists():
                try:
                    os.remove(srt_file)
                except:
                    pass
            
            return {
                'success': True,
                'output_path': output_path,
                'subtitle_file': srt_file if not subtitle_data else None
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'FFmpeg timeout (exceeded 5 minutes)'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }
    
    def _build_subtitle_filter(self, srt_file: str, style: Dict[str, Any]) -> str:
        """
        Build FFmpeg subtitle filter string
        
        Args:
            srt_file: Path to SRT file
            style: Style options
        
        Returns:
            FFmpeg filter string
        """
        # Escape file path for FFmpeg
        escaped_path = srt_file.replace('\\', '/').replace(':', '\\:')
        
        # Build subtitles filter with styling
        filter_parts = [
            f"subtitles='{escaped_path}'",
            f"force_style='FontSize={style.get('fontsize', 24)}"
        ]
        
        # Add style options
        style_opts = []
        if 'fontcolor' in style:
            style_opts.append(f"PrimaryColour={self._color_to_ass(style['fontcolor'])}")
        if 'outlinecolor' in style:
            style_opts.append(f"OutlineColour={self._color_to_ass(style['outlinecolor'])}")
        if 'outline' in style:
            style_opts.append(f"Outline={style['outline']}")
        if 'alignment' in style:
            style_opts.append(f"Alignment={style['alignment']}")
        if 'marginv' in style:
            style_opts.append(f"MarginV={style['marginv']}")
        
        if style_opts:
            filter_parts.append(','.join(style_opts))
        
        filter_parts.append("'")
        
        return ''.join(filter_parts)
    
    def _color_to_ass(self, color: str) -> str:
        """
        Convert color name/hex to ASS format (BGR hex)
        
        Args:
            color: Color name or hex code
        
        Returns:
            ASS color format (BGR hex)
        """
        color_map = {
            'white': '&HFFFFFF',
            'black': '&H000000',
            'yellow': '&H00FFFF',
            'red': '&H0000FF',
            'green': '&H00FF00',
            'blue': '&HFF0000'
        }
        
        if color.lower() in color_map:
            return color_map[color.lower()]
        
        # If hex, convert to BGR
        if color.startswith('#'):
            hex_color = color[1:]
            if len(hex_color) == 6:
                # Convert RGB to BGR
                r = hex_color[0:2]
                g = hex_color[2:4]
                b = hex_color[4:6]
                return f'&H{b}{g}{r}'
        
        return '&HFFFFFF'  # Default to white
    
    def embed_subtitles_from_text(
        self,
        video_path: str,
        text: str,
        topic: Optional[str] = None,
        output_path: Optional[str] = None,
        style: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate subtitles from text and embed into video
        
        Args:
            video_path: Path to input video
            text: Text content for subtitles
            topic: Optional topic for Wikipedia-based subtitles
            output_path: Output path
            style: Subtitle styling
        
        Returns:
            Result dictionary
        """
        # Get video duration for timing
        duration = self._get_video_duration(video_path)
        
        # Generate subtitles
        if topic:
            subtitle_data = self.subtitle_generator.generate_subtitles_from_wikipedia(
                topic, duration
            )
        else:
            subtitle_data = self.subtitle_generator.generate_subtitles_from_text(
                text, None
            )
        
        # Embed subtitles
        return self.embed_subtitles(
            video_path=video_path,
            subtitle_data=subtitle_data,
            output_path=output_path,
            style=style
        )
    
    def _get_video_duration(self, video_path: str) -> float:
        """Get video duration in seconds using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(video_path)
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return float(result.stdout.strip())
        except:
            pass
        return 180.0  # Default 3 minutes


# Global instance
subtitle_embedder = SubtitleEmbedder()

