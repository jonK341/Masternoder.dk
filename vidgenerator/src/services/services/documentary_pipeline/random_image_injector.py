"""
Random Image Injector Service
Searches through host/user pictures, movie_clips, web history
and injects random images into video frames during generation
"""
import os
import random
import glob
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image
import json


class RandomImageInjector:
    """Inject random images into video frames for engagement"""
    
    def __init__(self, base_path: Optional[str] = None):
        """Initialize image injector
        
        Args:
            base_path: Base path for searching images (default: user home)
        """
        self.base_path = base_path or str(Path.home())
        self.image_cache = []
        self.secrets_cache = []
        
    def discover_images(self, sources: List[str]) -> Dict[str, List[str]]:
        """Discover images from various sources
        
        Args:
            sources: List of sources to search ['user_pictures', 'movie_clips', 'web_history', 'secrets']
        
        Returns:
            Dictionary mapping source names to image paths
        """
        discovered = {}
        
        for source in sources:
            if source == 'user_pictures':
                discovered[source] = self._find_user_pictures()
            elif source == 'movie_clips':
                discovered[source] = self._find_movie_clips()
            elif source == 'web_history':
                discovered[source] = self._find_web_history_images()
            elif source == 'secrets':
                discovered[source] = self._find_secrets_images()
        
        return discovered
    
    def _find_user_pictures(self) -> List[str]:
        """Find user pictures from common directories"""
        pictures = []
        common_dirs = [
            os.path.join(self.base_path, 'Pictures'),
            os.path.join(self.base_path, 'Documents'),
            os.path.join(self.base_path, 'Downloads'),
            os.path.join(self.base_path, 'Desktop'),
        ]
        
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp']
        
        for dir_path in common_dirs:
            if os.path.exists(dir_path):
                for ext in extensions:
                    pictures.extend(glob.glob(os.path.join(dir_path, '**', ext), recursive=True))
        
        return pictures[:100]  # Limit to 100 images
    
    def _find_movie_clips(self) -> List[str]:
        """Find movie clip images (thumbnails, frames)"""
        clips = []
        
        # Search in project directories
        project_dirs = [
            os.path.join(self.base_path, 'UsecaseSampler', 'Micro', 'output'),
            os.path.join(self.base_path, 'UsecaseSampler', 'Micro', 'temp'),
        ]
        
        extensions = ['*.jpg', '*.jpeg', '*.png']
        
        for dir_path in project_dirs:
            if os.path.exists(dir_path):
                for ext in extensions:
                    clips.extend(glob.glob(os.path.join(dir_path, '**', ext), recursive=True))
        
        return clips[:50]  # Limit to 50 images
    
    def _find_web_history_images(self) -> List[str]:
        """Find images from web history (browser cache, downloads)"""
        web_images = []
        
        # Browser cache locations
        cache_dirs = [
            os.path.join(self.base_path, 'AppData', 'Local', 'Google', 'Chrome', 'User Data', 'Default', 'Cache'),
            os.path.join(self.base_path, 'AppData', 'Local', 'Microsoft', 'Edge', 'User Data', 'Default', 'Cache'),
        ]
        
        extensions = ['*.jpg', '*.jpeg', '*.png', '*.webp']
        
        for dir_path in cache_dirs:
            if os.path.exists(dir_path):
                for ext in extensions:
                    web_images.extend(glob.glob(os.path.join(dir_path, ext), recursive=False))
        
        return web_images[:100]  # Limit to 100 images
    
    def _find_secrets_images(self) -> List[str]:
        """Find special 'secrets' images for engagement (35 fps injection)"""
        secrets = []
        
        # Special secrets directory (can be configured)
        secrets_dir = os.path.join(self.base_path, '.secrets', 'images')
        
        if os.path.exists(secrets_dir):
            extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif']
            for ext in extensions:
                secrets.extend(glob.glob(os.path.join(secrets_dir, ext), recursive=True))
        
        # If no secrets directory, use random selection from other sources
        if not secrets:
            all_images = self._find_user_pictures() + self._find_movie_clips()
            secrets = random.sample(all_images, min(10, len(all_images)))
        
        return secrets[:20]  # Limit to 20 secrets images
    
    def inject_images_at_fps(self, video_duration: float, fps: float = 35.0, 
                            injection_rate: float = 1.0) -> List[Tuple[int, str]]:
        """Generate injection plan for images at specific FPS
        
        Args:
            video_duration: Video duration in seconds
            fps: Frames per second (default: 35.0 for secrets)
            injection_rate: How often to inject (1.0 = every frame, 0.5 = every other frame)
        
        Returns:
            List of (frame_number, image_path) tuples
        """
        total_frames = int(video_duration * fps)
        injections = []
        
        # Discover images
        all_images = []
        sources = self.discover_images(['user_pictures', 'movie_clips', 'web_history', 'secrets'])
        for image_list in sources.values():
            all_images.extend(image_list)
        
        if not all_images:
            return injections  # No images to inject
        
        # Calculate injection frequency
        injection_frequency = max(1, int(1.0 / injection_rate))
        
        # Inject images at specified rate
        for frame_num in range(0, total_frames, injection_frequency):
            image_path = random.choice(all_images)
            injections.append((frame_num, image_path))
        
        return injections
    
    def prepare_secrets_injections(self, video_duration: float, fps: float = 35.0) -> List[Dict]:
        """Prepare secrets image injections at 35 fps for engagement
        
        Args:
            video_duration: Video duration in seconds
            fps: Frames per second (default: 35.0)
        
        Returns:
            List of injection dictionaries with frame_number, image_path, timestamp
        """
        secrets = self._find_secrets_images()
        if not secrets:
            return []
        
        total_frames = int(video_duration * fps)
        injections = []
        
        for frame_num in range(0, total_frames, 35):  # Inject every 35 frames (1 per second at 35fps)
            timestamp = frame_num / fps
            image_path = random.choice(secrets)
            injections.append({
                'frame_number': frame_num,
                'image_path': image_path,
                'timestamp': timestamp,
                'fps': fps,
                'injection_type': 'secrets',
                'engagement': True
            })
        
        return injections

