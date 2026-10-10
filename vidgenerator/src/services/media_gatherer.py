"""
Media Gatherer Service
Collects images and audio from service worker and web pages for video generation
"""
import os
import json
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import hashlib
import shutil

class MediaGatherer:
    """Gathers and manages media files (images, audio) for video generation"""
    
    def __init__(self, storage_dir: Optional[str] = None):
        """
        Initialize media gatherer
        
        Args:
            storage_dir: Directory to store gathered media (default: output/media)
        """
        if storage_dir:
            self.storage_dir = Path(storage_dir)
        else:
            # Default storage location
            base_output = os.getenv('OUTPUT_DIR', 'output')
            current_path = Path(__file__).resolve()
            project_root = current_path.parent.parent.parent
            self.storage_dir = project_root / base_output / "media"
            
            # Check for production path
            if os.path.exists('/var/www/html/vidgenerator/output'):
                self.storage_dir = Path('/var/www/html/vidgenerator/output/media')
        
        # Create subdirectories
        self.images_dir = self.storage_dir / "images"
        self.audio_dir = self.storage_dir / "audio"
        self.metadata_file = self.storage_dir / "media_index.json"
        
        # Ensure directories exist
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        
        # Load media index
        self.media_index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load media index from file"""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[MediaGatherer] Error loading index: {e}")
                return {'images': [], 'audio': []}
        return {'images': [], 'audio': []}
    
    def _save_index(self):
        """Save media index to file"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.media_index, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[MediaGatherer] Error saving index: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate hash of file for deduplication"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ''
    
    def gather_image(self, image_url: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Download and store an image from URL
        
        Args:
            image_url: URL of the image
            metadata: Optional metadata (title, description, tags, etc.)
        
        Returns:
            Dictionary with file path, metadata, or None if failed
        """
        try:
            # Download image
            response = requests.get(image_url, timeout=30, stream=True)
            if response.status_code != 200:
                print(f"[MediaGatherer] Failed to download image: {response.status_code}")
                return None
            
            # Determine file extension from content type or URL
            content_type = response.headers.get('Content-Type', '')
            if 'jpeg' in content_type or 'jpg' in content_type:
                ext = '.jpg'
            elif 'png' in content_type:
                ext = '.png'
            elif 'gif' in content_type:
                ext = '.gif'
            elif 'webp' in content_type:
                ext = '.webp'
            else:
                # Try to get from URL
                ext = Path(image_url).suffix or '.jpg'
            
            # Generate filename from URL hash
            url_hash = hashlib.md5(image_url.encode()).hexdigest()[:12]
            filename = f"{url_hash}{ext}"
            file_path = self.images_dir / filename
            
            # Download and save
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check if file already exists (deduplication)
            file_hash = self._get_file_hash(file_path)
            existing = next(
                (item for item in self.media_index.get('images', []) if item.get('hash') == file_hash),
                None
            )
            
            if existing:
                # File already exists, return existing metadata
                return existing
            
            # Create metadata entry
            image_metadata = {
                'id': url_hash,
                'filename': filename,
                'path': str(file_path),
                'url': image_url,
                'hash': file_hash,
                'size': file_path.stat().st_size,
                'gathered_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'tags': metadata.get('tags', []) if metadata else [],
                'description': metadata.get('description', '') if metadata else ''
            }
            
            # Add to index
            if 'images' not in self.media_index:
                self.media_index['images'] = []
            self.media_index['images'].append(image_metadata)
            self._save_index()
            
            print(f"[MediaGatherer] Gathered image: {filename} ({file_path.stat().st_size} bytes)")
            return image_metadata
            
        except Exception as e:
            print(f"[MediaGatherer] Error gathering image: {e}")
            return None
    
    def gather_audio(self, audio_url: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """
        Download and store an audio file from URL
        
        Args:
            audio_url: URL of the audio file
            metadata: Optional metadata (title, description, duration, etc.)
        
        Returns:
            Dictionary with file path, metadata, or None if failed
        """
        try:
            # Download audio
            response = requests.get(audio_url, timeout=60, stream=True)
            if response.status_code != 200:
                print(f"[MediaGatherer] Failed to download audio: {response.status_code}")
                return None
            
            # Determine file extension
            content_type = response.headers.get('Content-Type', '')
            if 'mp3' in content_type:
                ext = '.mp3'
            elif 'wav' in content_type:
                ext = '.wav'
            elif 'ogg' in content_type:
                ext = '.ogg'
            elif 'm4a' in content_type:
                ext = '.m4a'
            else:
                ext = Path(audio_url).suffix or '.mp3'
            
            # Generate filename
            url_hash = hashlib.md5(audio_url.encode()).hexdigest()[:12]
            filename = f"{url_hash}{ext}"
            file_path = self.audio_dir / filename
            
            # Download and save
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Check for duplicates
            file_hash = self._get_file_hash(file_path)
            existing = next(
                (item for item in self.media_index.get('audio', []) if item.get('hash') == file_hash),
                None
            )
            
            if existing:
                return existing
            
            # Create metadata entry
            audio_metadata = {
                'id': url_hash,
                'filename': filename,
                'path': str(file_path),
                'url': audio_url,
                'hash': file_hash,
                'size': file_path.stat().st_size,
                'gathered_at': datetime.now().isoformat(),
                'metadata': metadata or {},
                'tags': metadata.get('tags', []) if metadata else [],
                'description': metadata.get('description', '') if metadata else '',
                'duration': metadata.get('duration', 0) if metadata else 0
            }
            
            # Add to index
            if 'audio' not in self.media_index:
                self.media_index['audio'] = []
            self.media_index['audio'].append(audio_metadata)
            self._save_index()
            
            print(f"[MediaGatherer] Gathered audio: {filename} ({file_path.stat().st_size} bytes)")
            return audio_metadata
            
        except Exception as e:
            print(f"[MediaGatherer] Error gathering audio: {e}")
            return None
    
    def search_images(self, query: str = None, tags: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for images by query or tags
        
        Args:
            query: Text query to search in descriptions
            tags: List of tags to filter by
            limit: Maximum number of results
        
        Returns:
            List of image metadata dictionaries
        """
        images = self.media_index.get('images', [])
        
        # Filter by query
        if query:
            query_lower = query.lower()
            images = [
                img for img in images
                if query_lower in img.get('description', '').lower() or
                   query_lower in img.get('url', '').lower() or
                   any(query_lower in tag.lower() for tag in img.get('tags', []))
            ]
        
        # Filter by tags
        if tags:
            images = [
                img for img in images
                if any(tag.lower() in [t.lower() for t in img.get('tags', [])] for tag in tags)
            ]
        
        # Sort by gathered_at (newest first)
        images.sort(key=lambda x: x.get('gathered_at', ''), reverse=True)
        
        return images[:limit]
    
    def search_audio(self, query: str = None, tags: List[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for audio files by query or tags
        
        Args:
            query: Text query to search in descriptions
            tags: List of tags to filter by
            limit: Maximum number of results
        
        Returns:
            List of audio metadata dictionaries
        """
        audio_files = self.media_index.get('audio', [])
        
        # Filter by query
        if query:
            query_lower = query.lower()
            audio_files = [
                aud for aud in audio_files
                if query_lower in aud.get('description', '').lower() or
                   query_lower in aud.get('url', '').lower() or
                   any(query_lower in tag.lower() for tag in aud.get('tags', []))
            ]
        
        # Filter by tags
        if tags:
            audio_files = [
                aud for aud in audio_files
                if any(tag.lower() in [t.lower() for t in aud.get('tags', [])] for tag in tags)
            ]
        
        # Sort by gathered_at (newest first)
        audio_files.sort(key=lambda x: x.get('gathered_at', ''), reverse=True)
        
        return audio_files[:limit]
    
    def get_media_for_prompt(self, prompt: str, num_images: int = 5, num_audio: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get relevant media files for a video generation prompt
        
        Args:
            prompt: Video generation prompt
            num_images: Number of images to retrieve
            num_audio: Number of audio files to retrieve
        
        Returns:
            Dictionary with 'images' and 'audio' lists
        """
        # Extract keywords from prompt for searching
        keywords = prompt.lower().split()
        
        # Search for images
        images = self.search_images(query=prompt, limit=num_images)
        
        # If not enough images, try keyword search
        if len(images) < num_images:
            for keyword in keywords[:5]:  # Try first 5 keywords
                additional = self.search_images(query=keyword, limit=num_images - len(images))
                images.extend(additional)
                if len(images) >= num_images:
                    break
        
        # Search for audio
        audio_files = self.search_audio(query=prompt, limit=num_audio)
        
        # If no audio found, get any available audio
        if not audio_files:
            audio_files = self.media_index.get('audio', [])[:num_audio]
        
        return {
            'images': images[:num_images],
            'audio': audio_files[:num_audio]
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about gathered media"""
        images = self.media_index.get('images', [])
        audio = self.media_index.get('audio', [])
        
        total_image_size = sum(img.get('size', 0) for img in images)
        total_audio_size = sum(aud.get('size', 0) for aud in audio)
        
        return {
            'total_images': len(images),
            'total_audio': len(audio),
            'total_image_size': total_image_size,
            'total_audio_size': total_audio_size,
            'total_size': total_image_size + total_audio_size,
            'storage_dir': str(self.storage_dir)
        }

