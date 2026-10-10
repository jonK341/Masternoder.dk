"""
Post Processor - Professional video enhancement pipeline
Includes color correction, noise reduction, sharpening, and optimization
"""
import os
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum


class ColorStyle(Enum):
    """Color grading styles"""
    STANDARD = "standard"
    CINEMATIC = "cinematic"
    VIBRANT = "vibrant"
    MUTED = "muted"
    WARM = "warm"
    COOL = "cool"


class PostProcessor:
    """Professional post-processing for video enhancement"""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize post processor
        
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
    
    def apply_color_correction(
        self,
        video_path: Path,
        style: ColorStyle = ColorStyle.STANDARD,
        output_path: Optional[Path] = None
    ) -> bool:
        """
        Apply color correction to video
        
        Args:
            video_path: Input video path
            style: Color style to apply
            output_path: Output path (overwrites input if None)
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Color correction filters
            color_filters = {
                ColorStyle.STANDARD: 'eq=contrast=1.1:brightness=0.02:saturation=1.05',
                ColorStyle.CINEMATIC: 'eq=contrast=1.2:brightness=-0.05:saturation=0.9:gamma=1.1',
                ColorStyle.VIBRANT: 'eq=contrast=1.15:brightness=0.05:saturation=1.2',
                ColorStyle.MUTED: 'eq=contrast=1.0:brightness=0.0:saturation=0.85',
                ColorStyle.WARM: 'eq=contrast=1.1:brightness=0.03:saturation=1.1,colorbalance=rs=0.1:gs=-0.05:bs=-0.1',
                ColorStyle.COOL: 'eq=contrast=1.1:brightness=0.02:saturation=1.05,colorbalance=rs=-0.1:gs=0.05:bs=0.1'
            }
            
            filter_str = color_filters.get(style, color_filters[ColorStyle.STANDARD])
            
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', filter_str,
                '-c:v', 'libx264',
                '-crf', '18',  # High quality
                '-preset', 'slow',
                '-c:a', 'copy',
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
            print(f"[PostProcessor] Color correction error: {e}")
            return False
    
    def reduce_noise(self, video_path: Path, output_path: Optional[Path] = None) -> bool:
        """
        Reduce video noise
        
        Args:
            video_path: Input video path
            output_path: Output path
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Use hqdn3d filter for noise reduction
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', 'hqdn3d=4:3:6:4.5',  # Light noise reduction
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'slow',
                '-c:a', 'copy',
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
            print(f"[PostProcessor] Noise reduction error: {e}")
            return False
    
    def enhance_sharpness(self, video_path: Path, output_path: Optional[Path] = None) -> bool:
        """
        Enhance video sharpness
        
        Args:
            video_path: Input video path
            output_path: Output path
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Use unsharp filter for sharpening
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', 'unsharp=5:5:1.0:5:5:0.0',  # Moderate sharpening
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'slow',
                '-c:a', 'copy',
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
            print(f"[PostProcessor] Sharpness enhancement error: {e}")
            return False
    
    def optimize_contrast(self, video_path: Path, output_path: Optional[Path] = None) -> bool:
        """
        Optimize video contrast
        
        Args:
            video_path: Input video path
            output_path: Output path
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Use curves filter for contrast optimization
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', 'curves=preset=medium_contrast',
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'slow',
                '-c:a', 'copy',
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
            print(f"[PostProcessor] Contrast optimization error: {e}")
            return False
    
    def process_full_pipeline(
        self,
        video_path: Path,
        color_style: ColorStyle = ColorStyle.STANDARD,
        reduce_noise_enabled: bool = True,
        enhance_sharpness_enabled: bool = True,
        optimize_contrast_enabled: bool = True,
        output_path: Optional[Path] = None
    ) -> bool:
        """
        Apply full post-processing pipeline
        
        Args:
            video_path: Input video path
            color_style: Color grading style
            reduce_noise_enabled: Enable noise reduction
            enhance_sharpness_enabled: Enable sharpness enhancement
            optimize_contrast_enabled: Enable contrast optimization
            output_path: Output path
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # Build combined filter
            filters = []
            
            # Color correction
            color_filters = {
                ColorStyle.STANDARD: 'eq=contrast=1.1:brightness=0.02:saturation=1.05',
                ColorStyle.CINEMATIC: 'eq=contrast=1.2:brightness=-0.05:saturation=0.9:gamma=1.1',
                ColorStyle.VIBRANT: 'eq=contrast=1.15:brightness=0.05:saturation=1.2',
                ColorStyle.MUTED: 'eq=contrast=1.0:brightness=0.0:saturation=0.85',
                ColorStyle.WARM: 'eq=contrast=1.1:brightness=0.03:saturation=1.1',
                ColorStyle.COOL: 'eq=contrast=1.1:brightness=0.02:saturation=1.05'
            }
            filters.append(color_filters.get(color_style, color_filters[ColorStyle.STANDARD]))
            
            # Noise reduction
            if reduce_noise_enabled:
                filters.append('hqdn3d=4:3:6:4.5')
            
            # Sharpness
            if enhance_sharpness_enabled:
                filters.append('unsharp=5:5:1.0:5:5:0.0')
            
            # Contrast
            if optimize_contrast_enabled:
                filters.append('curves=preset=medium_contrast')
            
            filter_complex = ','.join(filters)
            
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', filter_complex,
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'slow',
                '-c:a', 'copy',
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=600,  # 10 minute timeout for full pipeline
                text=True
            )
            
            return result.returncode == 0 and output_path.exists()
            
        except Exception as e:
            print(f"[PostProcessor] Full pipeline error: {e}")
            return False
    
    def process_hdr(self, video_path: Path, output_path: Optional[Path] = None) -> bool:
        """
        Process HDR video (tone mapping)
        
        Args:
            video_path: Input video path
            output_path: Output path
        
        Returns:
            True if successful
        """
        if not self.ffmpeg_path or not video_path.exists():
            return False
        
        if output_path is None:
            output_path = video_path
        
        try:
            # HDR tone mapping
            cmd = [
                self.ffmpeg_path,
                '-i', str(video_path),
                '-vf', 'zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p',
                '-c:v', 'libx264',
                '-crf', '18',
                '-preset', 'slow',
                '-c:a', 'copy',
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
            print(f"[PostProcessor] HDR processing error: {e}")
            return False

