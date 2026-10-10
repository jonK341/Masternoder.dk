"""
AI Magi Overlay - Adds AI Magi text overlay to MP4 videos
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any


class AIMagiOverlay:
    """Adds AI Magi overlay to video files"""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
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
    
    def add_ai_magi_overlay(
        self,
        video_path: Path,
        output_path: Path,
        magi_text: str = "🧠⚡ AI Magi",
        position: str = "bottom-right",
        opacity: float = 0.8
    ) -> bool:
        """Add AI Magi overlay to video"""
        if not self.ffmpeg_path:
            return False
        
        try:
            # Escape text for FFmpeg
            magi_text_escaped = magi_text.replace(':', '\\:').replace("'", "\\'")
            
            # Position mapping
            position_map = {
                'top-left': 'x=20:y=20',
                'top-right': 'x=w-tw-20:y=20',
                'bottom-left': 'x=20:y=h-th-20',
                'bottom-right': 'x=w-tw-20:y=h-th-20',
                'center': 'x=(w-text_w)/2:y=(h-text_h)/2'
            }
            pos = position_map.get(position, position_map['bottom-right'])
            
            # Build FFmpeg command
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', f"drawtext=text='{magi_text_escaped}':fontsize=32:fontcolor=white@0.8:{pos}:box=1:boxcolor=black@0.5:boxborderw=5",
                '-c:a', 'copy',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=300)
            
            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"[AIMagiOverlay] FFmpeg error: {result.stderr.decode('utf-8', errors='ignore')[:500]}")
                return False
                
        except Exception as e:
            print(f"[AIMagiOverlay] Error adding overlay: {e}")
            return False

