"""
Enhanced User Profile with JSON Storage
More functional user profiling stored in JSON file
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class EnhancedUserProfileJSON:
    """
    Enhanced User Profile with JSON Storage
    - More functional profiling
    - Stores in JSON file on computer
    - Integrated with point system
    """
    
    def __init__(self, data_dir: str = 'data/user_profiles'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def get_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile from JSON file"""
        file_path = os.path.join(self.data_dir, f'{user_id}_profile.json')
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[EnhancedUserProfile] Error loading profile: {e}")
        
        # Return default profile
        return self._get_default_profile(user_id)
    
    def save_profile(self, user_id: str, profile: Dict[str, Any]) -> bool:
        """Save user profile to JSON file"""
        try:
            file_path = os.path.join(self.data_dir, f'{user_id}_profile.json')
            
            # Add metadata
            profile['last_updated'] = datetime.utcnow().isoformat()
            profile['user_id'] = user_id
            profile['version'] = '2.0'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(profile, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[EnhancedUserProfile] Error saving profile: {e}")
            return False
    
    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user profile"""
        profile = self.get_profile(user_id)
        profile.update(updates)
        self.save_profile(user_id, profile)
        return profile
    
    def _get_default_profile(self, user_id: str) -> Dict[str, Any]:
        """Get default profile structure"""
        return {
            'user_id': user_id,
            'username': 'user_' + user_id[:8],
            'display_name': '',
            'profile_picture_url': None,
            'created_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat(),
            
            # Game stats
            'level': 1,
            'xp': 0,
            'coins': 0,
            'trophy_points': 0,
            
            # Preferences
            'preferences': {
                'theme': 'dark',
                'language': 'da',
                'notifications': True
            },
            
            # Activity tracking
            'activity': {
                'videos_created': 0,
                'videos_watched': 0,
                'battles_won': 0,
                'battles_lost': 0,
                'login_streak': 0,
                'last_login': None
            },
            
            # Social
            'social': {
                'friends': [],
                'followers': 0,
                'following': 0
            },
            
            # Skills and abilities
            'skills': {},
            'abilities': {},
            
            # Achievements
            'achievements': [],
            'trophies': [],
            
            # Preferences and settings
            'settings': {
                'privacy_level': 'public',
                'content_filter': 'standard'
            },
            
            # Metadata
            'version': '2.0'
        }
    
    def get_profile_summary(self, user_id: str) -> Dict[str, Any]:
        """Get profile summary"""
        profile = self.get_profile(user_id)
        
        return {
            'user_id': profile.get('user_id'),
            'username': profile.get('username'),
            'display_name': profile.get('display_name'),
            'level': profile.get('level', 1),
            'xp': profile.get('xp', 0),
            'coins': profile.get('coins', 0),
            'activity_summary': {
                'videos_created': profile.get('activity', {}).get('videos_created', 0),
                'battles_won': profile.get('activity', {}).get('battles_won', 0),
                'login_streak': profile.get('activity', {}).get('login_streak', 0)
            }
        }


# Global instance
enhanced_user_profile_json = EnhancedUserProfileJSON()

