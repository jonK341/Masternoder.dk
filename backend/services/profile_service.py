"""
Profile Service
Comprehensive user profile management with statistics and activity tracking
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os

try:
    from backend.services.enhanced_user_profile_json import enhanced_user_profile_json
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.quick_battle_system import quick_battle
    from backend.services.quest_system import quest_system
except ImportError:
    enhanced_user_profile_json = None
    unified_point_counter = None
    quick_battle = None
    quest_system = None


class ProfileService:
    """Comprehensive profile service with statistics and activity"""
    
    def __init__(self):
        self.activity_timeline_cache = {}  # user_id -> timeline_data
    
    def get_comprehensive_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive user profile with all statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            Complete profile data
        """
        profile = {}
        
        # Get base profile
        if enhanced_user_profile_json:
            profile = enhanced_user_profile_json.get_profile(user_id)
        else:
            profile = {
                'user_id': user_id,
                'username': f'user_{user_id[:8]}',
                'created_at': datetime.utcnow().isoformat()
            }
        
        # Get unified points
        points_data = {}
        if unified_point_counter:
            try:
                points_data = unified_point_counter.get_all_points(user_id)
            except:
                pass
        
        # Get battle statistics
        battle_stats = {}
        if quick_battle:
            try:
                battle_stats = quick_battle.get_user_battle_stats(user_id)
            except:
                pass
        
        # Get quest progress
        quest_progress = {}
        if quest_system:
            try:
                quest_progress = quest_system.get_user_progress(user_id)
            except:
                pass
        
        # Build comprehensive profile
        comprehensive = {
            'user_id': user_id,
            'username': profile.get('username', f'user_{user_id[:8]}'),
            'display_name': profile.get('display_name', ''),
            'avatar': profile.get('avatar', None),
            'profile_picture_url': profile.get('profile_picture_url'),
            'created_at': profile.get('created_at', datetime.utcnow().isoformat()),
            'last_active': profile.get('last_active', datetime.utcnow().isoformat()),
            
            # Points & Statistics
            'points': points_data,
            'total_points': sum([v for v in points_data.values() if isinstance(v, (int, float))]),
            
            # Battle Statistics
            'battle_stats': battle_stats,
            'battle_counter': battle_stats.get('counter', {}),
            'battle_streak': battle_stats.get('streak', {}),
            
            # Quest Progress
            'quest_progress': quest_progress,
            'active_quests': quest_progress.get('active_quests', []),
            'completed_quests': quest_progress.get('completed_quests', []),
            
            # Activity
            'activity': profile.get('activity', {}),
            'achievements': profile.get('achievements', []),
            'trophies': profile.get('trophies', []),
            
            # Preferences
            'preferences': profile.get('preferences', {}),
            'settings': profile.get('settings', {}),
            
            # Social
            'social': profile.get('social', {}),
            
            # Level & Progression
            'level': profile.get('level', 1),
            'xp': profile.get('xp', 0),
            'coins': profile.get('coins', 0),
        }
        
        return comprehensive
    
    def get_activity_timeline(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get user activity timeline
        
        Args:
            user_id: User identifier
            limit: Number of activities to return
            
        Returns:
            List of activities in chronological order
        """
        timeline = []
        
        # Get battle history
        if quick_battle:
            try:
                battle_stats = quick_battle.get_user_battle_stats(user_id)
                streak_history = battle_stats.get('streak', {}).get('recent_history', [])
                for battle in streak_history:
                    timeline.append({
                        'type': 'battle',
                        'action': 'won' if battle.get('won') else 'lost',
                        'timestamp': battle.get('timestamp'),
                        'data': battle
                    })
            except:
                pass
        
        # Get quest completions
        if quest_system:
            try:
                quest_progress = quest_system.get_user_progress(user_id)
                completed = quest_progress.get('completed_quests', [])
                for quest in completed[:10]:  # Last 10
                    timeline.append({
                        'type': 'quest',
                        'action': 'completed',
                        'timestamp': quest.get('completed_at'),
                        'data': quest
                    })
            except:
                pass
        
        # Get achievements
        if enhanced_user_profile_json:
            try:
                profile = enhanced_user_profile_json.get_profile(user_id)
                achievements = profile.get('achievements', [])
                for achievement in achievements[:10]:  # Last 10
                    timeline.append({
                        'type': 'achievement',
                        'action': 'unlocked',
                        'timestamp': achievement.get('unlocked_at'),
                        'data': achievement
                    })
            except:
                pass
        
        # Sort by timestamp (newest first)
        timeline.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return timeline[:limit]
    
    def update_profile(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update user profile
        
        Args:
            user_id: User identifier
            updates: Profile updates
            
        Returns:
            Updated profile
        """
        if enhanced_user_profile_json:
            return enhanced_user_profile_json.update_profile(user_id, updates)
        
        # Fallback: return updates
        return {
            'user_id': user_id,
            **updates,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def get_profile_statistics(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive profile statistics
        
        Args:
            user_id: User identifier
            
        Returns:
            Statistics dictionary
        """
        profile = self.get_comprehensive_profile(user_id)
        
        stats = {
            'total_points': profile.get('total_points', 0),
            'level': profile.get('level', 1),
            'xp': profile.get('xp', 0),
            'coins': profile.get('coins', 0),
            
            # Battle stats
            'battles_won': profile.get('battle_counter', {}).get('wins', 0),
            'battles_lost': profile.get('battle_counter', {}).get('losses', 0),
            'total_battles': profile.get('battle_counter', {}).get('total_battles', 0),
            'win_streak': profile.get('battle_streak', {}).get('current_streak', 0),
            'best_streak': profile.get('battle_streak', {}).get('best_streak', 0),
            
            # Quest stats
            'active_quests': len(profile.get('active_quests', [])),
            'completed_quests': len(profile.get('completed_quests', [])),
            
            # Achievement stats
            'achievements_count': len(profile.get('achievements', [])),
            'trophies_count': len(profile.get('trophies', [])),
            
            # Activity stats
            'videos_created': profile.get('activity', {}).get('videos_created', 0),
            'videos_watched': profile.get('activity', {}).get('videos_watched', 0),
            'login_streak': profile.get('activity', {}).get('login_streak', 0),
        }
        
        # Calculate win rate
        total = stats['battles_won'] + stats['battles_lost']
        stats['win_rate'] = (stats['battles_won'] / total * 100) if total > 0 else 0.0
        
        return stats
    
    def get_profile_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get profile summary for quick display
        
        Args:
            user_id: User identifier
            
        Returns:
            Profile summary
        """
        profile = self.get_comprehensive_profile(user_id)
        stats = self.get_profile_statistics(user_id)
        
        return {
            'user_id': user_id,
            'username': profile.get('username'),
            'display_name': profile.get('display_name'),
            'avatar': profile.get('avatar'),
            'level': profile.get('level', 1),
            'total_points': stats.get('total_points', 0),
            'battles_won': stats.get('battles_won', 0),
            'achievements_count': stats.get('achievements_count', 0),
            'rank': None  # Would be calculated from leaderboard
        }


# Global instance
profile_service = ProfileService()
