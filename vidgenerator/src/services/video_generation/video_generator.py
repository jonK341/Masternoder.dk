"""
Video Generator - Main interface for AI video generation
Supports multiple providers: RunwayML, Pika Labs, Stable Video Diffusion, and Placeholder
"""
import os
import time
import requests
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

# Load .env file if available (for API keys)
try:
    from dotenv import load_dotenv
    # Try to load .env from project root
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), '.env')
    if os.path.exists(env_path):
        load_dotenv(env_path)
    else:
        # Fallback: try current directory
        load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, use environment variables
except Exception:
    pass  # Ignore errors loading .env

# Import retry handler for API calls
try:
    from src.utils.retry_handler import RetryHandler
    RETRY_AVAILABLE = True
except ImportError:
    RETRY_AVAILABLE = False
    class RetryHandler:
        @staticmethod
        def retry(*args, **kwargs):
            def decorator(func):
                return func
            return decorator


class VideoProvider(ABC):
    """Base class for video generation providers"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (has API key)"""
        pass
    
    @abstractmethod
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "1280x768",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a video from a prompt"""
        pass


class RunwayMLProvider(VideoProvider):
    """RunwayML video generation provider"""
    
    def __init__(self):
        self.api_key = os.getenv('RUNWAYML_API_KEY', '')
        self.api_url = 'https://api.runwayml.com/v1/video/generate'
        self.model = 'gen3a_turbo'
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "1280x768",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate video using RunwayML API"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'RunwayML API key not configured'
            }
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'prompt': prompt,
                'duration': min(duration, 10),  # RunwayML max is 10 seconds
                'resolution': resolution,
                'model': self.model
            }
            
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'provider': 'runwayml',
                    'task_id': result.get('id'),
                    'video_url': result.get('video_url'),
                    'status': 'processing'
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}',
                    'provider': 'runwayml'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'runwayml'
            }


class PikaLabsProvider(VideoProvider):
    """Pika Labs video generation provider"""
    
    def __init__(self):
        self.api_key = os.getenv('PIKA_LABS_API_KEY', '')
        self.api_url = 'https://api.pikalabs.com/v1/generate'
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "1280x768",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate video using Pika Labs API"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'Pika Labs API key not configured'
            }
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'prompt': prompt,
                'duration': min(duration, 5),  # Pika Labs max is 5 seconds
                'resolution': resolution
            }
            
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'provider': 'pikalabs',
                    'task_id': result.get('task_id'),
                    'video_url': result.get('video_url'),
                    'status': 'processing'
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}',
                    'provider': 'pikalabs'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'pikalabs'
            }


class StableVideoDiffusionProvider(VideoProvider):
    """Stable Video Diffusion provider (Stability AI)"""
    
    def __init__(self):
        self.api_key = os.getenv('STABILITY_AI_API_KEY') or os.getenv('STABLE_VIDEO_API_KEY', '')
        self.api_url = 'https://api.stability.ai/v2alpha/generation/image-to-video'
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "1280x768",
        image_url: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate video using Stability AI's Stable Video Diffusion"""
        if not self.is_available():
            return {
                'success': False,
                'error': 'Stability AI API key not configured'
            }
        
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            
            # Stable Video Diffusion requires an image
            if not image_url:
                return {
                    'success': False,
                    'error': 'Stable Video Diffusion requires an image',
                    'provider': 'stable_video_diffusion'
                }
            
            data = {
                'image': image_url,
                'prompt': prompt,
                'duration': min(duration, 5),
            }
            
            response = requests.post(
                self.api_url,
                json=data,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    'success': True,
                    'provider': 'stable_video_diffusion',
                    'generation_id': result.get('id'),
                    'video_url': result.get('video_url'),
                    'status': 'processing'
                }
            else:
                return {
                    'success': False,
                    'error': f'API error: {response.status_code}',
                    'provider': 'stable_video_diffusion'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'provider': 'stable_video_diffusion'
            }


class PlaceholderVideoProvider(VideoProvider):
    """Placeholder provider that always works (for testing/fallback)"""
    
    def is_available(self) -> bool:
        return True  # Always available
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "1280x768",
        **kwargs
    ) -> Dict[str, Any]:
        """Generate placeholder video (for testing when no API keys are available)"""
        return {
            'success': True,
            'provider': 'placeholder',
            'is_placeholder': True,
            'video_url': None,  # Will be handled by video compiler
            'status': 'completed',
            'message': 'Placeholder video (no API keys configured)'
        }


class VideoGenerator:
    """Main video generator that uses available providers"""
    
    def __init__(self):
        """Initialize video generator with all providers"""
        self.providers = [
            RunwayMLProvider(),
            PikaLabsProvider(),
            StableVideoDiffusionProvider(),
            PlaceholderVideoProvider()  # Always last as fallback
        ]
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        available = []
        for provider in self.providers:
            if provider.is_available():
                provider_name = type(provider).__name__.replace('Provider', '').lower()
                available.append(provider_name)
        return available
    
    def get_best_provider(self) -> Optional[VideoProvider]:
        """Get the best available provider (prefer non-placeholder)"""
        for provider in self.providers:
            if provider.is_available() and not isinstance(provider, PlaceholderVideoProvider):
                return provider
        # Fallback to placeholder
        return self.providers[-1] if self.providers else None
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        resolution: str = "1280x768",
        provider_name: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a video using the best available provider
        
        Args:
            prompt: Text prompt describing the video
            duration: Video duration in seconds
            resolution: Video resolution (e.g., "1280x768")
            provider_name: Specific provider to use (optional)
            **kwargs: Additional provider-specific arguments
        
        Returns:
            Dictionary with success, provider, video_url, task_id, etc.
        """
        # Use specific provider if requested
        if provider_name:
            for provider in self.providers:
                if provider_name.lower() in type(provider).__name__.lower():
                    if provider.is_available():
                        return provider.generate_video(prompt, duration, resolution, **kwargs)
            return {
                'success': False,
                'error': f'Provider {provider_name} not available'
            }
        
        # Use best available provider
        provider = self.get_best_provider()
        if not provider:
            return {
                'success': False,
                'error': 'No video generation providers available'
            }
        
        return provider.generate_video(prompt, duration, resolution, **kwargs)

