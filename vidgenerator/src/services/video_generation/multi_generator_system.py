"""
Multi-AI Video Generator System
Supports multiple video generation APIs with intelligent distribution
"""
import os
import requests
import time
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass


class ClipDuration(Enum):
    """Clip duration categories"""
    SHORT = "short"  # 5-12 seconds
    MEDIUM = "medium"  # 1-3 minutes
    LONG = "long"  # 25-30 minutes (final documentary)


class GeneratorType(Enum):
    """Available video generator types"""
    RUNWAY = "runway"
    PIKA = "pika"
    STABLE_VIDEO = "stable_video"
    LUMALABS = "luma_labs"
    KREA = "krea"
    FALLBACK = "fallback"  # FFmpeg placeholder


@dataclass
class ClipRequest:
    """Request for clip generation"""
    prompt: str
    duration: ClipDuration
    duration_seconds: int
    style: Optional[str] = None
    aspect_ratio: str = "16:9"
    metadata: Optional[Dict] = None


@dataclass
class ClipResult:
    """Result from clip generation"""
    success: bool
    clip_path: Optional[str] = None
    generator_used: Optional[str] = None
    duration: Optional[float] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class MultiGeneratorSystem:
    """Manages multiple video generation APIs"""
    
    def __init__(self):
        self.generators = {}
        self.generator_configs = {
            GeneratorType.RUNWAY: {
                'enabled': os.getenv('RUNWAY_API_KEY') is not None,
                'api_key': os.getenv('RUNWAY_API_KEY'),
                'endpoint': 'https://api.runwayml.com/v1/generate',
                'max_duration': 10,  # seconds
                'best_for': [ClipDuration.SHORT]
            },
            GeneratorType.PIKA: {
                'enabled': os.getenv('PIKA_API_KEY') is not None,
                'api_key': os.getenv('PIKA_API_KEY'),
                'endpoint': 'https://api.pika.art/v1/generate',
                'max_duration': 4,  # seconds
                'best_for': [ClipDuration.SHORT]
            },
            GeneratorType.STABLE_VIDEO: {
                'enabled': os.getenv('STABLE_VIDEO_API_KEY') is not None,
                'api_key': os.getenv('STABLE_VIDEO_API_KEY'),
                'endpoint': 'https://api.stability.ai/v2beta/generation/video',
                'max_duration': 5,  # seconds
                'best_for': [ClipDuration.SHORT]
            },
            GeneratorType.LUMALABS: {
                'enabled': os.getenv('LUMA_API_KEY') is not None,
                'api_key': os.getenv('LUMA_API_KEY'),
                'endpoint': 'https://api.lumalabs.ai/v1/generate',
                'max_duration': 5,  # seconds
                'best_for': [ClipDuration.SHORT]
            },
            GeneratorType.FALLBACK: {
                'enabled': True,  # Always available
                'api_key': None,
                'endpoint': None,
                'max_duration': 300,  # 5 minutes
                'best_for': [ClipDuration.SHORT, ClipDuration.MEDIUM, ClipDuration.LONG]
            }
        }
        
        # Generator priority based on clip type
        self.generator_priority = {
            ClipDuration.SHORT: [
                GeneratorType.PIKA,
                GeneratorType.RUNWAY,
                GeneratorType.STABLE_VIDEO,
                GeneratorType.LUMALABS,
                GeneratorType.FALLBACK
            ],
            ClipDuration.MEDIUM: [
                GeneratorType.RUNWAY,
                GeneratorType.STABLE_VIDEO,
                GeneratorType.FALLBACK
            ],
            ClipDuration.LONG: [
                GeneratorType.FALLBACK  # Compile from shorter clips
            ]
        }
    
    def get_available_generators(self, clip_duration: ClipDuration) -> List[GeneratorType]:
        """Get list of available generators for a clip duration"""
        available = []
        priority_list = self.generator_priority.get(clip_duration, [GeneratorType.FALLBACK])
        
        for gen_type in priority_list:
            config = self.generator_configs.get(gen_type, {})
            if config.get('enabled', False):
                # Check if generator supports this duration
                max_dur = config.get('max_duration', 0)
                if clip_duration == ClipDuration.SHORT or max_dur >= 60:  # Short clips or generators that support longer
                    available.append(gen_type)
        
        # Always include fallback
        if GeneratorType.FALLBACK not in available:
            available.append(GeneratorType.FALLBACK)
        
        return available
    
    def generate_clip(self, request: ClipRequest) -> ClipResult:
        """Generate a clip using the best available generator"""
        available_generators = self.get_available_generators(request.duration)
        
        if not available_generators:
            return ClipResult(
                success=False,
                error="No generators available"
            )
        
        # Try generators in priority order
        for gen_type in available_generators:
            try:
                result = self._generate_with_generator(gen_type, request)
                if result.success:
                    return result
            except Exception as e:
                print(f"[MultiGenerator] Error with {gen_type.value}: {e}")
                continue
        
        # All generators failed, use fallback
        return self._generate_fallback(request)
    
    def _generate_with_generator(self, gen_type: GeneratorType, request: ClipRequest) -> ClipResult:
        """Generate clip with specific generator"""
        if gen_type == GeneratorType.FALLBACK:
            return self._generate_fallback(request)
        
        config = self.generator_configs.get(gen_type, {})
        if not config.get('enabled'):
            raise Exception(f"Generator {gen_type.value} not enabled")
        
        # This would call the actual API
        # For now, return a placeholder that indicates which generator would be used
        return ClipResult(
            success=False,
            error=f"Generator {gen_type.value} not yet implemented",
            generator_used=gen_type.value
        )
    
    def _generate_fallback(self, request: ClipRequest) -> ClipResult:
        """Generate clip using FFmpeg fallback (placeholder video)"""
        try:
            from src.utils.file_manager import FileManager
            file_manager = FileManager()
            
            # Create a placeholder video file
            clip_id = f"clip_{int(time.time())}"
            output_path = file_manager.get_output_path(f"{clip_id}.mp4")
            
            # Use FFmpeg to create a simple video
            import subprocess
            cmd = [
                'ffmpeg',
                '-f', 'lavfi',
                '-i', f'testsrc=duration={request.duration_seconds}:size=1920x1080:rate=30',
                '-pix_fmt', 'yuv420p',
                '-t', str(request.duration_seconds),
                '-y',
                str(output_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and os.path.exists(output_path):
                return ClipResult(
                    success=True,
                    clip_path=str(output_path),
                    generator_used=GeneratorType.FALLBACK.value,
                    duration=request.duration_seconds,
                    metadata={'method': 'ffmpeg_placeholder'}
                )
            else:
                return ClipResult(
                    success=False,
                    error=f"FFmpeg failed: {result.stderr}",
                    generator_used=GeneratorType.FALLBACK.value
                )
        except Exception as e:
            return ClipResult(
                success=False,
                error=str(e),
                generator_used=GeneratorType.FALLBACK.value
            )
    
    def generate_multiple_clips(self, requests: List[ClipRequest]) -> List[ClipResult]:
        """Generate multiple clips in parallel"""
        results = []
        for request in requests:
            result = self.generate_clip(request)
            results.append(result)
        return results

