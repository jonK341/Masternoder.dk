"""
Quality Engine - Adaptive quality system for A+ video generation
Provides intelligent quality calculation, optimization, and validation
"""
import os
from typing import Dict, Any, Optional, Tuple
from enum import Enum
from pathlib import Path


class QualityLevel(Enum):
    """Quality levels for video generation"""
    ULTRA = "ultra"      # A+ quality: 4K, 60fps, HDR, maximum bitrate
    PREMIUM = "premium"  # High quality: 1080p, 30fps, high bitrate
    HIGH = "high"        # Good quality: 1080p, 24fps, medium bitrate
    MEDIUM = "medium"    # Standard quality: 720p, 24fps
    LOW = "low"          # Basic quality: 480p, 24fps (for testing)


class QualityEngine:
    """Intelligent quality engine for video generation"""
    
    # Quality presets
    QUALITY_PRESETS = {
        QualityLevel.ULTRA: {
            'resolution': '3840x2160',      # 4K
            'width': 3840,
            'height': 2160,
            'fps': 60,
            'bitrate': '20M',
            'crf': 15,                     # Lower = better quality
            'preset': 'slow',               # Slower = better quality
            'color_depth': 10,              # 10-bit color
            'audio_bitrate': '320k',
            'audio_sample_rate': 48000,
            'hdr': True,
            'post_processing': True,
            'color_grading': True,
            'transitions': 'professional'
        },
        QualityLevel.PREMIUM: {
            'resolution': '1920x1080',      # Full HD
            'width': 1920,
            'height': 1080,
            'fps': 30,
            'bitrate': '10M',
            'crf': 18,
            'preset': 'medium',
            'color_depth': 8,
            'audio_bitrate': '192k',
            'audio_sample_rate': 48000,
            'hdr': False,
            'post_processing': True,
            'color_grading': True,
            'transitions': 'smooth'
        },
        QualityLevel.HIGH: {
            'resolution': '1920x1080',
            'width': 1920,
            'height': 1080,
            'fps': 24,
            'bitrate': '5M',
            'crf': 20,
            'preset': 'medium',
            'color_depth': 8,
            'audio_bitrate': '128k',
            'audio_sample_rate': 44100,
            'hdr': False,
            'post_processing': True,
            'color_grading': False,
            'transitions': 'crossfade'
        },
        QualityLevel.MEDIUM: {
            'resolution': '1280x720',       # HD
            'width': 1280,
            'height': 720,
            'fps': 24,
            'bitrate': '2M',
            'crf': 23,
            'preset': 'fast',
            'color_depth': 8,
            'audio_bitrate': '128k',
            'audio_sample_rate': 44100,
            'hdr': False,
            'post_processing': False,
            'color_grading': False,
            'transitions': 'crossfade'
        },
        QualityLevel.LOW: {
            'resolution': '854x480',        # SD
            'width': 854,
            'height': 480,
            'fps': 24,
            'bitrate': '1M',
            'crf': 28,
            'preset': 'ultrafast',
            'color_depth': 8,
            'audio_bitrate': '96k',
            'audio_sample_rate': 44100,
            'hdr': False,
            'post_processing': False,
            'color_grading': False,
            'transitions': 'none'
        }
    }
    
    def __init__(self):
        """Initialize quality engine"""
        pass
    
    def calculate_optimal_quality(
        self,
        content_type: str = 'documentary',
        duration: int = 180,
        complexity: str = 'medium',
        user_quality: Optional[str] = None
    ) -> QualityLevel:
        """
        Calculate optimal quality level based on content characteristics
        
        Args:
            content_type: Type of content (documentary, entertainment, etc.)
            duration: Video duration in seconds
            complexity: Content complexity (simple, medium, complex)
            user_quality: User-requested quality level (overrides calculation)
        
        Returns:
            Optimal QualityLevel
        """
        # If user specified quality, use it (with validation)
        if user_quality:
            try:
                quality = QualityLevel(user_quality.lower())
                return quality
            except ValueError:
                pass  # Invalid quality, calculate instead
        
        # Calculate based on content characteristics
        score = 0
        
        # Content type scoring
        content_scores = {
            'documentary': 3,
            'entertainment': 2,
            'educational': 3,
            'promotional': 4,
            'default': 2
        }
        score += content_scores.get(content_type.lower(), 2)
        
        # Duration scoring (longer = higher quality needed)
        if duration >= 600:  # 10+ minutes
            score += 2
        elif duration >= 300:  # 5+ minutes
            score += 1
        
        # Complexity scoring
        complexity_scores = {
            'complex': 2,
            'medium': 1,
            'simple': 0
        }
        score += complexity_scores.get(complexity.lower(), 1)
        
        # Map score to quality level
        if score >= 7:
            return QualityLevel.ULTRA
        elif score >= 5:
            return QualityLevel.PREMIUM
        elif score >= 3:
            return QualityLevel.HIGH
        elif score >= 1:
            return QualityLevel.MEDIUM
        else:
            return QualityLevel.LOW
    
    def get_quality_settings(self, quality_level: QualityLevel) -> Dict[str, Any]:
        """
        Get quality settings for a quality level
        
        Args:
            quality_level: QualityLevel enum
        
        Returns:
            Dictionary with quality settings
        """
        return self.QUALITY_PRESETS.get(quality_level, self.QUALITY_PRESETS[QualityLevel.MEDIUM]).copy()
    
    def optimize_encoding_settings(
        self,
        quality_level: QualityLevel,
        content_type: str = 'documentary'
    ) -> Dict[str, Any]:
        """
        Get optimized encoding settings for FFmpeg
        
        Args:
            quality_level: QualityLevel enum
            content_type: Type of content
        
        Returns:
            Dictionary with FFmpeg encoding settings
        """
        settings = self.get_quality_settings(quality_level)
        
        # Content-specific optimizations
        if content_type.lower() == 'documentary':
            # Documentaries benefit from higher quality
            if quality_level == QualityLevel.HIGH:
                settings['crf'] = max(18, settings['crf'] - 2)
        elif content_type.lower() == 'entertainment':
            # Entertainment can use faster encoding
            if settings['preset'] == 'slow':
                settings['preset'] = 'medium'
        
        return settings
    
    def validate_quality_level(self, quality_str: str) -> bool:
        """
        Validate if quality string is valid
        
        Args:
            quality_str: Quality string to validate
        
        Returns:
            True if valid
        """
        try:
            QualityLevel(quality_str.lower())
            return True
        except ValueError:
            return False
    
    def get_ffmpeg_quality_args(self, quality_level: QualityLevel) -> Dict[str, str]:
        """
        Get FFmpeg command arguments for quality level
        
        Args:
            quality_level: QualityLevel enum
        
        Returns:
            Dictionary with FFmpeg arguments
        """
        settings = self.get_quality_settings(quality_level)
        
        return {
            'resolution': settings['resolution'],
            'crf': str(settings['crf']),
            'preset': settings['preset'],
            'fps': str(settings['fps']),
            'bitrate': settings['bitrate'],
            'audio_bitrate': settings['audio_bitrate'],
            'audio_sample_rate': str(settings['audio_sample_rate'])
        }
    
    def should_apply_post_processing(self, quality_level: QualityLevel) -> bool:
        """Check if post-processing should be applied"""
        settings = self.get_quality_settings(quality_level)
        return settings.get('post_processing', False)
    
    def should_apply_color_grading(self, quality_level: QualityLevel) -> bool:
        """Check if color grading should be applied"""
        settings = self.get_quality_settings(quality_level)
        return settings.get('color_grading', False)
    
    def get_transition_type(self, quality_level: QualityLevel) -> str:
        """Get transition type for quality level"""
        settings = self.get_quality_settings(quality_level)
        return settings.get('transitions', 'crossfade')
    
    def is_hdr_enabled(self, quality_level: QualityLevel) -> bool:
        """Check if HDR is enabled for quality level"""
        settings = self.get_quality_settings(quality_level)
        return settings.get('hdr', False)

