"""
Quality Validator - Validates and scores video quality
Provides comprehensive quality metrics and validation
"""
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class QualityScore:
    """Quality score result"""
    overall_score: float  # 0.0 - 1.0
    resolution_score: float
    bitrate_score: float
    framerate_score: float
    audio_score: float
    visual_score: float
    sync_score: float
    artifacts: List[str]
    is_valid: bool
    meets_a_plus: bool  # 0.95+


@dataclass
class Artifact:
    """Video artifact detected"""
    type: str  # 'blocking', 'blur', 'noise', 'sync', etc.
    severity: str  # 'critical', 'major', 'minor'
    description: str
    timestamp: Optional[float] = None


class QualityValidator:
    """Validates video quality and calculates quality scores"""
    
    def __init__(self, ffmpeg_path: Optional[str] = None):
        """
        Initialize quality validator
        
        Args:
            ffmpeg_path: Path to FFmpeg executable (auto-detected if None)
        """
        self.ffmpeg_path = ffmpeg_path or self._find_ffmpeg()
        self.a_plus_threshold = 0.95
        self.minimum_threshold = 0.70
    
    def _find_ffmpeg(self) -> Optional[str]:
        """Find FFmpeg executable"""
        possible_paths = [
            'ffmpeg',
            'ffprobe',
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
    
    def validate_video(self, video_path: Path) -> QualityScore:
        """
        Validate video and calculate quality score
        
        Args:
            video_path: Path to video file
        
        Returns:
            QualityScore object with detailed metrics
        """
        if not video_path.exists():
            return QualityScore(
                overall_score=0.0,
                resolution_score=0.0,
                bitrate_score=0.0,
                framerate_score=0.0,
                audio_score=0.0,
                visual_score=0.0,
                sync_score=0.0,
                artifacts=['File not found'],
                is_valid=False,
                meets_a_plus=False
            )
        
        # Get video metadata
        metadata = self._get_video_metadata(video_path)
        if not metadata:
            return QualityScore(
                overall_score=0.0,
                resolution_score=0.0,
                bitrate_score=0.0,
                framerate_score=0.0,
                audio_score=0.0,
                visual_score=0.0,
                sync_score=0.0,
                artifacts=['Could not read video metadata'],
                is_valid=False,
                meets_a_plus=False
            )
        
        # Calculate individual scores
        resolution_score = self._score_resolution(metadata)
        bitrate_score = self._score_bitrate(metadata)
        framerate_score = self._score_framerate(metadata)
        audio_score = self._score_audio(metadata)
        visual_score = self._score_visual(video_path, metadata)
        sync_score = self._score_sync(metadata)
        
        # Detect artifacts
        artifacts = self._detect_artifacts(video_path, metadata)
        
        # Calculate overall score (weighted average)
        weights = {
            'resolution': 0.20,
            'bitrate': 0.15,
            'framerate': 0.10,
            'audio': 0.15,
            'visual': 0.25,
            'sync': 0.15
        }
        
        overall_score = (
            resolution_score * weights['resolution'] +
            bitrate_score * weights['bitrate'] +
            framerate_score * weights['framerate'] +
            audio_score * weights['audio'] +
            visual_score * weights['visual'] +
            sync_score * weights['sync']
        )
        
        # Penalize for artifacts
        artifact_penalty = min(len(artifacts) * 0.05, 0.20)
        overall_score = max(0.0, overall_score - artifact_penalty)
        
        is_valid = overall_score >= self.minimum_threshold
        meets_a_plus = overall_score >= self.a_plus_threshold
        
        return QualityScore(
            overall_score=round(overall_score, 3),
            resolution_score=round(resolution_score, 3),
            bitrate_score=round(bitrate_score, 3),
            framerate_score=round(framerate_score, 3),
            audio_score=round(audio_score, 3),
            visual_score=round(visual_score, 3),
            sync_score=round(sync_score, 3),
            artifacts=[a.description for a in artifacts],
            is_valid=is_valid,
            meets_a_plus=meets_a_plus
        )
    
    def _get_video_metadata(self, video_path: Path) -> Optional[Dict[str, Any]]:
        """Get video metadata using ffprobe"""
        if not self.ffmpeg_path:
            return None
        
        try:
            # Use ffprobe (usually same directory as ffmpeg)
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg', 'ffprobe')
            if not os.path.exists(ffprobe_path):
                ffprobe_path = 'ffprobe'
            
            cmd = [
                ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(video_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=30,
                text=True
            )
            
            if result.returncode != 0:
                return None
            
            import json
            data = json.loads(result.stdout)
            
            # Extract video and audio streams
            video_stream = None
            audio_stream = None
            
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                elif stream.get('codec_type') == 'audio' and not audio_stream:
                    audio_stream = stream
            
            format_info = data.get('format', {})
            
            return {
                'video_stream': video_stream,
                'audio_stream': audio_stream,
                'format': format_info,
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'bitrate': int(format_info.get('bit_rate', 0))
            }
            
        except Exception as e:
            try:
                print(f"[QualityValidator] Error getting metadata: {e}")
            except Exception:
                print(f"[QualityValidator] Error getting metadata (encoding issue)")
            return None
    
    def _score_resolution(self, metadata: Dict[str, Any]) -> float:
        """Score video resolution (0.0 - 1.0)"""
        video_stream = metadata.get('video_stream')
        if not video_stream:
            return 0.0
        
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        
        # Score based on resolution
        if width >= 3840 and height >= 2160:  # 4K
            return 1.0
        elif width >= 1920 and height >= 1080:  # Full HD
            return 0.9
        elif width >= 1280 and height >= 720:  # HD
            return 0.7
        elif width >= 854 and height >= 480:  # SD
            return 0.5
        else:
            return 0.3
    
    def _score_bitrate(self, metadata: Dict[str, Any]) -> float:
        """Score video bitrate (0.0 - 1.0)"""
        bitrate = metadata.get('bitrate', 0)
        
        # Score based on bitrate (in bps)
        if bitrate >= 20_000_000:  # 20 Mbps
            return 1.0
        elif bitrate >= 10_000_000:  # 10 Mbps
            return 0.9
        elif bitrate >= 5_000_000:  # 5 Mbps
            return 0.75
        elif bitrate >= 2_000_000:  # 2 Mbps
            return 0.6
        elif bitrate >= 1_000_000:  # 1 Mbps
            return 0.4
        else:
            return 0.2
    
    def _score_framerate(self, metadata: Dict[str, Any]) -> float:
        """Score video framerate (0.0 - 1.0)"""
        video_stream = metadata.get('video_stream')
        if not video_stream:
            return 0.0
        
        # Parse framerate (can be "30/1" or "30")
        fps_str = video_stream.get('r_frame_rate', '0/1')
        try:
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den)
            else:
                fps = float(fps_str)
        except (ValueError, ZeroDivisionError):
            fps = 0.0
        
        # Score based on framerate
        if fps >= 60:
            return 1.0
        elif fps >= 30:
            return 0.9
        elif fps >= 24:
            return 0.8
        elif fps >= 20:
            return 0.6
        else:
            return 0.4
    
    def _score_audio(self, metadata: Dict[str, Any]) -> float:
        """Score audio quality (0.0 - 1.0)"""
        audio_stream = metadata.get('audio_stream')
        if not audio_stream:
            return 0.5  # No audio is acceptable for some videos
        
        bitrate = int(audio_stream.get('bit_rate', 0))
        sample_rate = int(audio_stream.get('sample_rate', 0))
        
        # Score audio bitrate
        if bitrate >= 320_000:  # 320 kbps
            bitrate_score = 1.0
        elif bitrate >= 192_000:  # 192 kbps
            bitrate_score = 0.9
        elif bitrate >= 128_000:  # 128 kbps
            bitrate_score = 0.7
        elif bitrate >= 96_000:  # 96 kbps
            bitrate_score = 0.5
        else:
            bitrate_score = 0.3
        
        # Score sample rate
        if sample_rate >= 48000:
            sample_rate_score = 1.0
        elif sample_rate >= 44100:
            sample_rate_score = 0.9
        else:
            sample_rate_score = 0.7
        
        return (bitrate_score + sample_rate_score) / 2
    
    def _score_visual(self, video_path: Path, metadata: Dict[str, Any]) -> float:
        """Score visual quality (0.0 - 1.0) - simplified for now"""
        # Basic visual scoring based on codec and resolution
        video_stream = metadata.get('video_stream')
        if not video_stream:
            return 0.5
        
        codec = video_stream.get('codec_name', '').lower()
        width = int(video_stream.get('width', 0))
        
        # Codec scoring
        if codec in ['h265', 'hevc']:
            codec_score = 1.0
        elif codec in ['h264', 'avc']:
            codec_score = 0.9
        else:
            codec_score = 0.7
        
        # Resolution scoring (already done, but use for visual)
        if width >= 1920:
            res_score = 1.0
        elif width >= 1280:
            res_score = 0.8
        else:
            res_score = 0.6
        
        return (codec_score + res_score) / 2
    
    def _score_sync(self, metadata: Dict[str, Any]) -> float:
        """Score audio-video sync (0.0 - 1.0)"""
        # Simplified sync scoring - assume good sync if both streams exist
        video_stream = metadata.get('video_stream')
        audio_stream = metadata.get('audio_stream')
        
        if not video_stream:
            return 0.0
        if not audio_stream:
            return 0.8  # No audio is acceptable
        
        # Check if durations match (rough sync check)
        video_duration = float(video_stream.get('duration', 0))
        audio_duration = float(audio_stream.get('duration', 0))
        
        if video_duration > 0 and audio_duration > 0:
            diff = abs(video_duration - audio_duration)
            if diff < 0.1:  # Within 0.1 seconds
                return 1.0
            elif diff < 0.5:  # Within 0.5 seconds
                return 0.9
            elif diff < 1.0:  # Within 1 second
                return 0.7
            else:
                return 0.5
        
        return 0.8  # Default: assume good sync
    
    def _detect_artifacts(self, video_path: Path, metadata: Dict[str, Any]) -> List[Artifact]:
        """Detect video artifacts"""
        artifacts = []
        
        # Check for common issues
        video_stream = metadata.get('video_stream')
        if not video_stream:
            artifacts.append(Artifact(
                type='missing_stream',
                severity='critical',
                description='Video stream missing'
            ))
            return artifacts
        
        # Check resolution
        width = int(video_stream.get('width', 0))
        height = int(video_stream.get('height', 0))
        if width < 854 or height < 480:
            artifacts.append(Artifact(
                type='low_resolution',
                severity='major',
                description=f'Low resolution: {width}x{height}'
            ))
        
        # Check bitrate
        bitrate = metadata.get('bitrate', 0)
        if bitrate < 1_000_000:  # Less than 1 Mbps
            artifacts.append(Artifact(
                type='low_bitrate',
                severity='major',
                description=f'Low bitrate: {bitrate / 1_000_000:.1f} Mbps'
            ))
        
        # Check codec
        codec = video_stream.get('codec_name', '').lower()
        if codec not in ['h264', 'h265', 'hevc', 'avc']:
            artifacts.append(Artifact(
                type='non_standard_codec',
                severity='minor',
                description=f'Non-standard codec: {codec}'
            ))
        
        return artifacts
    
    def check_audio_sync(self, video_path: Path) -> bool:
        """Check if audio and video are in sync"""
        metadata = self._get_video_metadata(video_path)
        if not metadata:
            return False
        
        sync_score = self._score_sync(metadata)
        return sync_score >= 0.8
    
    def calculate_quality_score(self, video_path: Path) -> float:
        """Calculate overall quality score (0.0 - 1.0)"""
        quality_score = self.validate_video(video_path)
        return quality_score.overall_score

