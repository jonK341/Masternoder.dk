"""
AI Provider Integrations for Video Generation
Implements actual AI service calls to generate video clips
"""

from typing import Dict, Any, Optional
import os
import json
import requests
from pathlib import Path


class AIProviderManager:
    """Manages multiple AI providers for video generation"""
    
    def __init__(self):
        self.providers = {
            'openai': OpenAIProvider(),
            'replicate': ReplicateProvider(),
            'runway': RunwayProvider(),
            'pika': PikaProvider(),
            'stable_video': StableVideoProvider(),
            'ffmpeg_fallback': FFmpegFallbackProvider()
        }
        self.active_providers = self._detect_available_providers()
    
    def _detect_available_providers(self) -> list:
        """Detect which providers are available based on API keys"""
        available = []
        for name, provider in self.providers.items():
            if provider.is_available():
                available.append(name)
                # print(f"[AIProviderManager] ✓ {name} is available")  # Disabled to prevent errno 11
            else:
                pass  # Empty else block
                # print(f"[AIProviderManager] ✗ {name} is not available")  # Disabled to prevent errno 11
        return available
    
    def generate_video(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        provider: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using best available provider"""
        
        # Select provider
        if provider and provider in self.active_providers:
            selected_provider = self.providers[provider]
        elif self.active_providers:
            # Use first available provider
            selected_provider = self.providers[self.active_providers[0]]
        else:
            # Fallback to ffmpeg
            selected_provider = self.providers['ffmpeg_fallback']
        
    # print(f"[AIProviderManager] Using provider: {selected_provider.__class__.__name__}")  # Disabled to prevent errno 11
        
        # Generate video
        try:
            result = selected_provider.generate(
                prompt=prompt,
                duration=duration,
                image_url=image_url,
                output_path=output_path
            )
            return result
        except Exception as e:
    # print(f"[AIProviderManager] Error generating video: {e}")  # Disabled to prevent errno 11
            import traceback
            traceback.print_exc()
            return None


class BaseAIProvider:
    """Base class for AI providers"""
    
    def is_available(self) -> bool:
        """Check if provider is available (has API key, etc.)"""
        return False
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video clip"""
        raise NotImplementedError


class OpenAIProvider(BaseAIProvider):
    """OpenAI Sora API provider (when available)"""
    
    def is_available(self) -> bool:
        api_key = os.getenv('OPENAI_API_KEY')
        return api_key is not None and len(api_key) > 0
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using OpenAI Sora"""
        try:
            import openai
            
            client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            print(f"[OpenAIProvider] Generating video with prompt: {prompt[:50]}...")
            
            # Sora API call (when available)
            response = client.videos.generate(
                model="sora",
                prompt=prompt,
                duration=duration
            )
            
            video_url = response.data[0].url if response.data else None
            
            if video_url and output_path:
                # Download video
                video_path = self._download_video(video_url, output_path)
                if video_path:
                    return {
                        'video_path': video_path,
                        'video_url': video_url,
                        'quality_score': 0.9,
                        'provider': 'openai'
                    }
            
            return {
                'video_url': video_url,
                'quality_score': 0.9,
                'provider': 'openai'
            }
        except Exception as e:
            print(f"[OpenAIProvider] Error: {e}")
            return None
    
    def _download_video(self, url: str, output_path: str) -> Optional[str]:
        """Download video from URL"""
        try:
            response = requests.get(url, timeout=120, stream=True)
            response.raise_for_status()
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                return output_path
            return None
        except Exception as e:
            print(f"[OpenAIProvider] Download error: {e}")
            return None


class ReplicateProvider(BaseAIProvider):
    """Replicate AI provider for video generation"""
    
    def is_available(self) -> bool:
        api_token = os.getenv('REPLICATE_API_TOKEN')
        return api_token is not None and len(api_token) > 0
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using Replicate"""
        try:
            import replicate
            
            print(f"[ReplicateProvider] Generating video with prompt: {prompt[:50]}...")
            
            # Use Stable Video Diffusion or similar model
            model = "stability-ai/stable-video-diffusion"
            
            input_data = {
                "prompt": prompt,
                "duration": min(duration, 5)  # Replicate typically supports up to 5 seconds
            }
            
            if image_url:
                input_data["image"] = image_url
            
            output = replicate.run(model, input=input_data)
            
            video_url = output if isinstance(output, str) else output[0] if output else None
            
            if video_url and output_path:
                video_path = self._download_video(video_url, output_path)
                if video_path:
                    return {
                        'video_path': video_path,
                        'video_url': video_url,
                        'quality_score': 0.8,
                        'provider': 'replicate'
                    }
            
            return {
                'video_url': video_url,
                'quality_score': 0.8,
                'provider': 'replicate'
            }
        except Exception as e:
            print(f"[ReplicateProvider] Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _download_video(self, url: str, output_path: str) -> Optional[str]:
        """Download video from URL"""
        try:
            response = requests.get(url, timeout=120, stream=True)
            response.raise_for_status()
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                return output_path
            return None
        except Exception as e:
            print(f"[ReplicateProvider] Download error: {e}")
            return None


class RunwayProvider(BaseAIProvider):
    """Runway ML provider"""
    
    def is_available(self) -> bool:
        api_key = os.getenv('RUNWAY_API_KEY')
        return api_key is not None and len(api_key) > 0
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using Runway ML"""
        # Runway API implementation would go here
        # For now, return None to fall back to other providers
        print(f"[RunwayProvider] Runway API not fully implemented yet")
        return None


class PikaProvider(BaseAIProvider):
    """Pika Labs provider"""
    
    def is_available(self) -> bool:
        api_key = os.getenv('PIKA_API_KEY')
        return api_key is not None and len(api_key) > 0
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using Pika Labs"""
        # Pika API implementation would go here
        print(f"[PikaProvider] Pika API not fully implemented yet")
        return None


class StableVideoProvider(BaseAIProvider):
    """Stable Video Diffusion provider (via Replicate)"""
    
    def is_available(self) -> bool:
        # Uses Replicate, so check Replicate token
        return ReplicateProvider().is_available()
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using Stable Video Diffusion"""
        # Use Replicate provider with Stable Video model
        replicate_provider = ReplicateProvider()
        if replicate_provider.is_available():
            return replicate_provider.generate(prompt, duration, image_url, output_path)
        return None


class FFmpegFallbackProvider(BaseAIProvider):
    """FFmpeg fallback provider - creates videos with text overlays"""
    
    def is_available(self) -> bool:
        # FFmpeg is always available as fallback
        return True
    
    def generate(
        self,
        prompt: str,
        duration: int = 10,
        image_url: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate video using FFmpeg with text overlay"""
        try:
            import subprocess
            
            if not output_path:
                output_path = f"/tmp/ffmpeg_video_{os.getpid()}.mp4"
            
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            
            # Escape prompt for ffmpeg
            text_escaped = prompt.replace("'", "\\'").replace(":", "\\:")[:100]
            
            # Create video with text overlay
            subprocess.run([
                'ffmpeg', '-f', 'lavfi', '-i', f'color=c=black:s=1920x1080:d={duration}',
                '-vf', f"drawtext=text='{text_escaped}':x=(w-text_w)/2:y=(h-text_h)/2:fontsize=48:fontcolor=white:box=1:boxcolor=0x00000000@1:boxborderw=10",
                '-c:v', 'libx264', '-t', str(duration), '-y', output_path
            ], check=True, timeout=60, capture_output=True)
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 10240:
                return {
                    'video_path': output_path,
                    'quality_score': 0.5,
                    'provider': 'ffmpeg_fallback'
                }
            
            return None
        except Exception as e:
            print(f"[FFmpegFallbackProvider] Error: {e}")
            return None

