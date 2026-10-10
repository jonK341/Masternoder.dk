"""Flexible video generator with support for multiple AI providers (RunwayML, Pika Labs, Stable Video Diffusion)"""
import os
import time
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from pathlib import Path


class VideoGeneratorProvider(ABC):
    """Abstract base class for video generation providers"""
    
    @abstractmethod
    def generate_video(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate video from prompt and return video file path and metadata"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available and configured"""
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get provider name"""
        pass


class RunwayMLProvider(VideoGeneratorProvider):
    """RunwayML Gen-3 video generation provider"""
    
    def __init__(self, api_key: str = None, model: str = None):
        """Initialize RunwayML provider"""
        self.api_key = api_key or os.getenv('RUNWAYML_API_KEY', '')
        self.model = model or os.getenv('RUNWAYML_MODEL', 'gen3a_turbo')
        self.base_url = os.getenv('RUNWAYML_BASE_URL', 'https://api.runwayml.com/v1')
        self.enabled = self.is_available()
    
    def is_available(self) -> bool:
        """Check if RunwayML is available and configured"""
        return bool(self.api_key)
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return 'RunwayML Gen-3'
    
    def generate_video(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate video using RunwayML Gen-3 API"""
        if not self.enabled:
            return None
        
        try:
            import requests
            
            # RunwayML Gen-3 API endpoint
            url = f"{self.base_url}/image-to-video"
            
            # Prepare request
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Parameters
            params = {
                'prompt': prompt,
                'model': self.model,
                'duration': kwargs.get('duration', 10),  # Default 10 seconds
                'resolution': kwargs.get('resolution', '1280x768')
            }
            
            # If image provided, use image-to-video, otherwise use text-to-video
            image_url = kwargs.get('image_url')
            if image_url:
                params['image'] = image_url
                response = requests.post(url, headers=headers, json=params, timeout=60)
            else:
                # Text-to-video endpoint
                url = f"{self.base_url}/text-to-video"
                response = requests.post(url, headers=headers, json=params, timeout=60)
            
            response.raise_for_status()
            result = response.json()
            
            # RunwayML returns a task ID, need to poll for completion
            task_id = result.get('id')
            if task_id:
                # Poll for video completion
                video_url = self._poll_task_status(task_id, headers)
                if video_url:
                    return {
                        'success': True,
                        'video_url': video_url,
                        'provider': 'runwayml',
                        'model': self.model,
                        'task_id': task_id
                    }
            
            return None
            
        except Exception as e:
            print(f"RunwayML generation error: {e}")
            return None
    
    def _poll_task_status(self, task_id: str, headers: dict, max_attempts: int = 60) -> Optional[str]:
        """Poll RunwayML task status until complete"""
        try:
            import requests
            
            url = f"{self.base_url}/tasks/{task_id}"
            
            for attempt in range(max_attempts):
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                status = data.get('status')
                if status == 'succeeded':
                    return data.get('output', [None])[0] if data.get('output') else None
                elif status == 'failed':
                    print(f"RunwayML task failed: {data.get('error', 'Unknown error')}")
                    return None
                
                # Wait before next poll
                time.sleep(2)
            
            print(f"RunwayML task timeout after {max_attempts} attempts")
            return None
            
        except Exception as e:
            print(f"RunwayML polling error: {e}")
            return None


class PikaLabsProvider(VideoGeneratorProvider):
    """Pika Labs video generation provider"""
    
    def __init__(self, api_key: str = None):
        """Initialize Pika Labs provider"""
        self.api_key = api_key or os.getenv('PIKA_LABS_API_KEY', '')
        self.base_url = os.getenv('PIKA_LABS_BASE_URL', 'https://api.pikalabs.com/v1')
        self.enabled = self.is_available()
    
    def is_available(self) -> bool:
        """Check if Pika Labs is available and configured"""
        return bool(self.api_key)
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return 'Pika Labs'
    
    def generate_video(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate video using Pika Labs API"""
        if not self.enabled:
            return None
        
        try:
            import requests
            
            # Pika Labs API endpoint
            url = f"{self.base_url}/generate"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Prepare request parameters
            params = {
                'prompt': prompt,
                'duration': kwargs.get('duration', 10),
                'fps': kwargs.get('fps', 24),
                'aspect_ratio': kwargs.get('aspect_ratio', '16:9')
            }
            
            # If image provided, use image-to-video
            image_url = kwargs.get('image_url')
            if image_url:
                params['image_url'] = image_url
                url = f"{self.base_url}/image-to-video"
            
            response = requests.post(url, headers=headers, json=params, timeout=60)
            response.raise_for_status()
            result = response.json()
            
            # Pika Labs returns video URL directly or task ID
            video_url = result.get('video_url') or result.get('url')
            if video_url:
                return {
                    'success': True,
                    'video_url': video_url,
                    'provider': 'pika_labs',
                    'task_id': result.get('task_id')
                }
            
            # If task ID, poll for completion
            task_id = result.get('task_id')
            if task_id:
                video_url = self._poll_task_status(task_id, headers)
                if video_url:
                    return {
                        'success': True,
                        'video_url': video_url,
                        'provider': 'pika_labs',
                        'task_id': task_id
                    }
            
            return None
            
        except Exception as e:
            print(f"Pika Labs generation error: {e}")
            return None
    
    def _poll_task_status(self, task_id: str, headers: dict, max_attempts: int = 60) -> Optional[str]:
        """Poll Pika Labs task status until complete"""
        try:
            import requests
            
            url = f"{self.base_url}/tasks/{task_id}"
            
            for attempt in range(max_attempts):
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                status = data.get('status')
                if status == 'completed':
                    return data.get('video_url') or data.get('url')
                elif status == 'failed':
                    print(f"Pika Labs task failed: {data.get('error', 'Unknown error')}")
                    return None
                
                time.sleep(2)
            
            print(f"Pika Labs task timeout after {max_attempts} attempts")
            return None
            
        except Exception as e:
            print(f"Pika Labs polling error: {e}")
            return None


class StableVideoDiffusionProvider(VideoGeneratorProvider):
    """Stable Video Diffusion provider (Stability AI)"""
    
    def __init__(self, api_key: str = None):
        """Initialize Stable Video Diffusion provider"""
        self.api_key = api_key or os.getenv('STABLE_VIDEO_API_KEY', os.getenv('STABILITY_AI_API_KEY', ''))
        self.base_url = os.getenv('STABLE_VIDEO_BASE_URL', 'https://api.stability.ai/v2alpha')
        self.enabled = self.is_available()
    
    def is_available(self) -> bool:
        """Check if Stable Video Diffusion is available and configured"""
        return bool(self.api_key)
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return 'Stable Video Diffusion'
    
    def generate_video(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate video using Stable Video Diffusion API"""
        if not self.enabled:
            return None
        
        try:
            import requests
            import base64
            from io import BytesIO
            
            # Stable Video Diffusion requires an image input
            image_url = kwargs.get('image_url')
            image_data = kwargs.get('image_data')
            
            if not image_url and not image_data:
                # Try to use prompt as image generation first (not ideal, but workable)
                print("Stable Video Diffusion requires an image - skipping")
                return None
            
            url = f"{self.base_url}/image-to-video"
            
            headers = {
                'Authorization': f'Bearer {self.api_key}',
            }
            
            # Prepare form data
            files = {}
            data = {
                'seed': kwargs.get('seed', 0),
                'cfg_scale': kwargs.get('cfg_scale', 1.8),
                'motion_bucket_id': kwargs.get('motion_bucket_id', 127)
            }
            
            # Handle image input
            if image_url:
                # Download image
                img_response = requests.get(image_url, timeout=30)
                img_response.raise_for_status()
                files['image'] = ('image.jpg', BytesIO(img_response.content), 'image/jpeg')
            elif image_data:
                if isinstance(image_data, str) and image_data.startswith('data:image'):
                    # Base64 encoded image
                    header, encoded = image_data.split(',', 1)
                    files['image'] = ('image.jpg', BytesIO(base64.b64decode(encoded)), 'image/jpeg')
                else:
                    files['image'] = ('image.jpg', BytesIO(image_data), 'image/jpeg')
            
            response = requests.post(url, headers=headers, files=files, data=data, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            # Stability AI returns generation ID, need to poll
            generation_id = result.get('id')
            if generation_id:
                video_url = self._poll_generation_status(generation_id, headers)
                if video_url:
                    return {
                        'success': True,
                        'video_url': video_url,
                        'provider': 'stable_video_diffusion',
                        'generation_id': generation_id
                    }
            
            return None
            
        except Exception as e:
            print(f"Stable Video Diffusion generation error: {e}")
            return None
    
    def _poll_generation_status(self, generation_id: str, headers: dict, max_attempts: int = 120) -> Optional[str]:
        """Poll Stability AI generation status until complete"""
        try:
            import requests
            
            url = f"{self.base_url}/image-to-video/result/{generation_id}"
            
            for attempt in range(max_attempts):
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                state = data.get('state')
                if state == 'complete':
                    # Download video from URL
                    video_url = data.get('video')
                    if video_url:
                        return video_url
                elif state == 'failed':
                    print(f"Stable Video Diffusion generation failed: {data.get('errors', 'Unknown error')}")
                    return None
                
                time.sleep(3)
            
            print(f"Stable Video Diffusion generation timeout after {max_attempts} attempts")
            return None
            
        except Exception as e:
            print(f"Stable Video Diffusion polling error: {e}")
            return None


class PlaceholderVideoProvider(VideoGeneratorProvider):
    """Placeholder video provider for development/testing"""
    
    def is_available(self) -> bool:
        """Placeholder is always available"""
        return True
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return 'Placeholder'
    
    def generate_video(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate placeholder video"""
        # Return placeholder - actual video generation not implemented
        return {
            'success': True,
            'video_url': None,  # Will be created as placeholder file
            'provider': 'placeholder',
            'is_placeholder': True
        }


class VideoGenerator:
    """Manages multiple video generation providers with systematic fallback"""
    
    def __init__(self):
        """Initialize video generator with available providers"""
        self.providers: list[VideoGeneratorProvider] = []
        
        # Initialize providers in order of preference
        provider_order = os.getenv('VIDEO_PROVIDER_ORDER', 'runwayml,pika_labs,stable_video,placeholder').split(',')
        provider_order = [p.strip() for p in provider_order]
        
        # Initialize RunwayML
        if 'runwayml' in provider_order:
            runwayml = RunwayMLProvider()
            if runwayml.enabled:
                self.providers.append(runwayml)
                print(f"[VideoGenerator] Enabled: {runwayml.get_provider_name()}")
        
        # Initialize Pika Labs
        if 'pika_labs' in provider_order:
            pika = PikaLabsProvider()
            if pika.enabled:
                self.providers.append(pika)
                print(f"[VideoGenerator] Enabled: {pika.get_provider_name()}")
        
        # Initialize Stable Video Diffusion
        if 'stable_video' in provider_order:
            svd = StableVideoDiffusionProvider()
            if svd.enabled:
                self.providers.append(svd)
                print(f"[VideoGenerator] Enabled: {svd.get_provider_name()}")
        
        # Add placeholder as fallback if no providers available
        if not self.providers or 'placeholder' in provider_order:
            placeholder = PlaceholderVideoProvider()
            self.providers.append(placeholder)
            print(f"[VideoGenerator] Enabled: {placeholder.get_provider_name()} (fallback)")
        
        if not self.providers:
            print("[VideoGenerator] Warning: No video providers available")
    
    def generate_video(self, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate video using first available provider with fallback"""
        for provider in self.providers:
            if not provider.is_available():
                continue
            
            try:
                print(f"[VideoGenerator] Attempting generation with {provider.get_provider_name()}...")
                result = provider.generate_video(prompt, **kwargs)
                
                if result and result.get('success'):
                    print(f"[VideoGenerator] Success with {provider.get_provider_name()}")
                    return result
                else:
                    print(f"[VideoGenerator] Failed with {provider.get_provider_name()}, trying next provider...")
            
            except Exception as e:
                print(f"[VideoGenerator] Error with {provider.get_provider_name()}: {e}, trying next provider...")
                continue
        
        print("[VideoGenerator] All providers failed")
        return None
    
    def get_available_providers(self) -> list[str]:
        """Get list of available provider names"""
        return [p.get_provider_name() for p in self.providers if p.is_available()]

