"""
Avatar Service
Handles avatar upload, storage, and management
"""
from typing import Dict, Any, Optional
from datetime import datetime
import os
import uuid
import base64
from PIL import Image
import io

try:
    from backend.services.enhanced_user_profile_json import enhanced_user_profile_json
except ImportError:
    enhanced_user_profile_json = None


class AvatarService:
    """Service for managing user avatars"""
    
    def __init__(self, upload_dir: str = 'data/avatars', max_size: int = 5 * 1024 * 1024):
        """
        Initialize avatar service
        
        Args:
            upload_dir: Directory for storing avatars
            max_size: Maximum file size in bytes (default: 5MB)
        """
        self.upload_dir = upload_dir
        self.max_size = max_size
        self.allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        self.avatar_sizes = {
            'thumbnail': (64, 64),
            'small': (128, 128),
            'medium': (256, 256),
            'large': (512, 512)
        }
        os.makedirs(upload_dir, exist_ok=True)
        os.makedirs(os.path.join(upload_dir, 'thumbnails'), exist_ok=True)
    
    def upload_avatar(self, user_id: str, file_data: bytes, filename: str) -> Dict[str, Any]:
        """
        Upload and process avatar image
        
        Args:
            user_id: User identifier
            file_data: Image file data
            filename: Original filename
            
        Returns:
            Upload result with avatar URLs
        """
        try:
            # Validate file size
            if len(file_data) > self.max_size:
                return {
                    'success': False,
                    'error': f'File size exceeds maximum of {self.max_size / 1024 / 1024}MB'
                }
            
            # Validate extension
            ext = os.path.splitext(filename)[1].lower()
            if ext not in self.allowed_extensions:
                return {
                    'success': False,
                    'error': f'Invalid file type. Allowed: {", ".join(self.allowed_extensions)}'
                }
            
            # Generate unique filename
            avatar_id = str(uuid.uuid4())
            avatar_filename = f'{avatar_id}{ext}'
            avatar_path = os.path.join(self.upload_dir, avatar_filename)
            
            # Save original
            with open(avatar_path, 'wb') as f:
                f.write(file_data)
            
            # Process and create thumbnails
            try:
                img = Image.open(io.BytesIO(file_data))
                img = img.convert('RGB')  # Convert to RGB for consistency
                
                # Create thumbnails
                avatar_urls = {}
                for size_name, (width, height) in self.avatar_sizes.items():
                    thumbnail = img.copy()
                    thumbnail.thumbnail((width, height), Image.Resampling.LANCZOS)
                    
                    if size_name == 'thumbnail':
                        thumb_path = os.path.join(self.upload_dir, 'thumbnails', avatar_filename)
                    else:
                        thumb_path = os.path.join(self.upload_dir, f'{avatar_id}_{size_name}{ext}')
                    
                    thumbnail.save(thumb_path, 'JPEG', quality=85)
                    avatar_urls[size_name] = f'/vidgenerator/static/avatars/{os.path.basename(thumb_path)}'
                
                # Save original processed
                img.save(avatar_path, 'JPEG', quality=90)
                avatar_urls['original'] = f'/vidgenerator/static/avatars/{avatar_filename}'
                
            except Exception as e:
                # If image processing fails, still save original
                avatar_urls = {
                    'original': f'/vidgenerator/static/avatars/{avatar_filename}'
                }
            
            # Update user profile
            if enhanced_user_profile_json:
                profile = enhanced_user_profile_json.get_profile(user_id)
                profile['avatar'] = avatar_urls.get('medium', avatar_urls.get('original'))
                profile['avatar_urls'] = avatar_urls
                profile['avatar_uploaded_at'] = datetime.utcnow().isoformat()
                enhanced_user_profile_json.save_profile(user_id, profile)
            
            return {
                'success': True,
                'avatar_id': avatar_id,
                'avatar_urls': avatar_urls,
                'message': 'Avatar uploaded successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error uploading avatar: {str(e)}'
            }
    
    def upload_avatar_base64(self, user_id: str, base64_data: str) -> Dict[str, Any]:
        """
        Upload avatar from base64 data
        
        Args:
            user_id: User identifier
            base64_data: Base64 encoded image data (with or without data URL prefix)
            
        Returns:
            Upload result
        """
        try:
            # Remove data URL prefix if present
            if ',' in base64_data:
                header, data = base64_data.split(',', 1)
                # Extract format from header
                if 'png' in header.lower():
                    ext = '.png'
                elif 'jpeg' in header.lower() or 'jpg' in header.lower():
                    ext = '.jpg'
                elif 'gif' in header.lower():
                    ext = '.gif'
                elif 'webp' in header.lower():
                    ext = '.webp'
                else:
                    ext = '.jpg'
            else:
                data = base64_data
                ext = '.jpg'
            
            # Decode base64
            file_data = base64.b64decode(data)
            filename = f'avatar{ext}'
            
            return self.upload_avatar(user_id, file_data, filename)
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing base64 avatar: {str(e)}'
            }
    
    def delete_avatar(self, user_id: str) -> Dict[str, Any]:
        """
        Delete user's avatar
        
        Args:
            user_id: User identifier
            
        Returns:
            Deletion result
        """
        try:
            if enhanced_user_profile_json:
                profile = enhanced_user_profile_json.get_profile(user_id)
                avatar_urls = profile.get('avatar_urls', {})
                
                # Delete files
                for url in avatar_urls.values():
                    if url.startswith('/vidgenerator/static/avatars/'):
                        filename = os.path.basename(url)
                        file_path = os.path.join(self.upload_dir, filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)
                
                # Update profile
                profile['avatar'] = None
                profile['avatar_urls'] = {}
                enhanced_user_profile_json.save_profile(user_id, profile)
            
            return {
                'success': True,
                'message': 'Avatar deleted successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error deleting avatar: {str(e)}'
            }
    
    def get_avatar_url(self, user_id: str, size: str = 'medium') -> Optional[str]:
        """
        Get user's avatar URL
        
        Args:
            user_id: User identifier
            size: Avatar size (thumbnail, small, medium, large, original)
            
        Returns:
            Avatar URL or None
        """
        if enhanced_user_profile_json:
            profile = enhanced_user_profile_json.get_profile(user_id)
            avatar_urls = profile.get('avatar_urls', {})
            return avatar_urls.get(size) or avatar_urls.get('medium') or avatar_urls.get('original')
        return None


# Global instance
avatar_service = AvatarService()
