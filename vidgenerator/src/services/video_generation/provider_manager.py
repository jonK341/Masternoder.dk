"""
Provider Manager - Intelligent provider selection and management
Selects best provider for each clip based on content type and quality requirements
"""
import os
from typing import Dict, Any, Optional, List
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed


class ProviderType(Enum):
    """Video generation provider types"""
    RUNWAYML = "runwayml"
    PIKA_LABS = "pika_labs"
    STABLE_VIDEO = "stable_video"
    PLACEHOLDER = "placeholder"


class ProviderManager:
    """Intelligent provider management for video generation"""
    
    # Provider capabilities and strengths
    PROVIDER_CAPABILITIES = {
        ProviderType.RUNWAYML: {
            'max_duration': 10,
            'max_resolution': '1920x1080',
            'strengths': ['realistic', 'documentary', 'cinematic'],
            'quality': 'high',
            'speed': 'medium',
            'cost': 'high'
        },
        ProviderType.PIKA_LABS: {
            'max_duration': 5,
            'max_resolution': '1280x768',
            'strengths': ['creative', 'animated', 'artistic'],
            'quality': 'medium',
            'speed': 'fast',
            'cost': 'medium'
        },
        ProviderType.STABLE_VIDEO: {
            'max_duration': 5,
            'max_resolution': '1280x768',
            'strengths': ['image_to_video', 'stable', 'consistent'],
            'quality': 'medium',
            'speed': 'medium',
            'cost': 'medium'
        },
        ProviderType.PLACEHOLDER: {
            'max_duration': 999,
            'max_resolution': '1280x768',
            'strengths': ['always_available'],
            'quality': 'low',
            'speed': 'instant',
            'cost': 'free'
        }
    }
    
    def __init__(self):
        """Initialize provider manager"""
        self.providers = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available providers"""
        try:
            from src.services.video_generation.video_generator import (
                VideoGenerator, RunwayMLProvider, PikaLabsProvider,
                StableVideoDiffusionProvider, PlaceholderVideoProvider
            )
            
            self.video_generator = VideoGenerator()
            
            # Map provider instances
            for provider in self.video_generator.providers:
                if isinstance(provider, RunwayMLProvider):
                    self.providers[ProviderType.RUNWAYML] = provider
                elif isinstance(provider, PikaLabsProvider):
                    self.providers[ProviderType.PIKA_LABS] = provider
                elif isinstance(provider, StableVideoDiffusionProvider):
                    self.providers[ProviderType.STABLE_VIDEO] = provider
                elif isinstance(provider, PlaceholderVideoProvider):
                    self.providers[ProviderType.PLACEHOLDER] = provider
                    
        except ImportError as e:
            print(f"[ProviderManager] Error initializing providers: {e}")
        except Exception as e:
            print(f"[ProviderManager] Error initializing providers: {e}")
            import traceback
            traceback.print_exc()
    
    def select_best_provider(
        self,
        prompt: str,
        quality_level: str = 'high',
        content_type: str = 'documentary',
        duration: int = 5,
        resolution: str = "1280x768"
    ) -> Optional[ProviderType]:
        """
        Select best provider for given requirements
        
        Args:
            prompt: Video generation prompt
            quality_level: Quality level (ultra, premium, high, medium, low)
            content_type: Type of content (documentary, entertainment, etc.)
            duration: Video duration in seconds
            resolution: Target resolution
        
        Returns:
            Best ProviderType or None if none available
        """
        # Score each available provider
        provider_scores = {}
        
        for provider_type, provider in self.providers.items():
            if not provider.is_available():
                continue
            
            # Skip placeholder unless no other options
            if provider_type == ProviderType.PLACEHOLDER:
                continue
            
            score = self._score_provider(
                provider_type,
                prompt,
                quality_level,
                content_type,
                duration,
                resolution
            )
            
            provider_scores[provider_type] = score
        
        # If no providers scored, use placeholder
        if not provider_scores:
            if ProviderType.PLACEHOLDER in self.providers:
                return ProviderType.PLACEHOLDER
            return None
        
        # Return provider with highest score
        best_provider = max(provider_scores.items(), key=lambda x: x[1])
        return best_provider[0]
    
    def _score_provider(
        self,
        provider_type: ProviderType,
        prompt: str,
        quality_level: str,
        content_type: str,
        duration: int,
        resolution: str
    ) -> float:
        """Score a provider for given requirements (0.0 - 1.0)"""
        capabilities = self.PROVIDER_CAPABILITIES.get(provider_type, {})
        score = 0.5  # Base score
        
        # Duration compatibility
        max_duration = capabilities.get('max_duration', 5)
        if duration <= max_duration:
            score += 0.2
        else:
            score -= 0.3  # Penalty for exceeding max duration
        
        # Quality match
        provider_quality = capabilities.get('quality', 'medium')
        quality_scores = {
            'ultra': {'high': 1.0, 'medium': 0.5, 'low': 0.2},
            'premium': {'high': 0.9, 'medium': 0.7, 'low': 0.3},
            'high': {'high': 0.8, 'medium': 0.6, 'low': 0.4},
            'medium': {'high': 0.6, 'medium': 0.8, 'low': 0.5},
            'low': {'high': 0.4, 'medium': 0.6, 'low': 0.8}
        }
        
        quality_match = quality_scores.get(quality_level, {}).get(provider_quality, 0.5)
        score += quality_match * 0.3
        
        # Content type match
        strengths = capabilities.get('strengths', [])
        content_type_lower = content_type.lower()
        
        if content_type_lower in ['documentary', 'realistic', 'cinematic']:
            if 'realistic' in strengths or 'documentary' in strengths or 'cinematic' in strengths:
                score += 0.2
        elif content_type_lower in ['entertainment', 'creative', 'artistic']:
            if 'creative' in strengths or 'artistic' in strengths:
                score += 0.2
        elif content_type_lower in ['animated', 'cartoon']:
            if 'animated' in strengths:
                score += 0.2
        
        # Speed bonus (faster is better for user experience)
        speed = capabilities.get('speed', 'medium')
        if speed == 'fast':
            score += 0.1
        elif speed == 'slow':
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def generate_parallel(
        self,
        clips: List[Dict[str, Any]],
        max_parallel: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple clips in parallel
        
        Args:
            clips: List of clip specifications (prompt, duration, etc.)
            max_parallel: Maximum parallel generations
        
        Returns:
            List of generation results
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=max_parallel) as executor:
            # Submit all tasks
            future_to_clip = {}
            for clip in clips:
                provider_type = self.select_best_provider(
                    prompt=clip.get('prompt', ''),
                    quality_level=clip.get('quality', 'high'),
                    content_type=clip.get('content_type', 'documentary'),
                    duration=clip.get('duration', 5),
                    resolution=clip.get('resolution', '1280x768')
                )
                
                if provider_type and provider_type in self.providers:
                    provider = self.providers[provider_type]
                    future = executor.submit(
                        provider.generate_video,
                        prompt=clip.get('prompt', ''),
                        duration=clip.get('duration', 5),
                        resolution=clip.get('resolution', '1280x768'),
                        **clip.get('kwargs', {})
                    )
                    future_to_clip[future] = clip
            
            # Collect results as they complete
            for future in as_completed(future_to_clip):
                clip = future_to_clip[future]
                try:
                    result = future.result()
                    result['clip_index'] = clip.get('index', len(results))
                    results.append(result)
                except Exception as e:
                    results.append({
                        'success': False,
                        'error': str(e),
                        'clip_index': clip.get('index', len(results))
                    })
        
        # Sort by clip index to maintain order
        results.sort(key=lambda x: x.get('clip_index', 0))
        return results
    
    def intelligent_fallback(
        self,
        failed_provider: ProviderType,
        prompt: str,
        quality_level: str = 'high',
        content_type: str = 'documentary'
    ) -> Optional[ProviderType]:
        """
        Find fallback provider when one fails
        
        Args:
            failed_provider: Provider that failed
            prompt: Video generation prompt
            quality_level: Quality level
            content_type: Content type
        
        Returns:
            Fallback ProviderType or None
        """
        # Get all available providers except the failed one
        available = []
        for provider_type, provider in self.providers.items():
            if provider_type != failed_provider and provider.is_available():
                available.append(provider_type)
        
        if not available:
            # Last resort: placeholder
            if ProviderType.PLACEHOLDER in self.providers:
                return ProviderType.PLACEHOLDER
            return None
        
        # Select best from available
        if len(available) == 1:
            return available[0]
        
        # Score remaining providers
        best_score = -1
        best_provider = None
        
        for provider_type in available:
            score = self._score_provider(
                provider_type,
                prompt,
                quality_level,
                content_type,
                duration=5,
                resolution='1280x768'
            )
            if score > best_score:
                best_score = score
                best_provider = provider_type
        
        return best_provider
    
    def get_provider_info(self, provider_type: ProviderType) -> Dict[str, Any]:
        """Get information about a provider"""
        capabilities = self.PROVIDER_CAPABILITIES.get(provider_type, {})
        provider = self.providers.get(provider_type)
        
        return {
            'type': provider_type.value,
            'available': provider.is_available() if provider else False,
            'capabilities': capabilities
        }

