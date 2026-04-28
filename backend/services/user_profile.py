"""
User Profile Service
Enhanced profile service with display, stats, and analytics methods
"""
import os
import json
from typing import Dict, Optional, Any
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class UserProfile:
    """Service for user profile management"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        
        # Initialize dependencies
        try:
            from backend.services.user_onboarding import user_onboarding
            self.onboarding = user_onboarding
        except:
            self.onboarding = None
        
        try:
            from backend.services.user_agent_skills import user_agent_skills
            self.agent_skills = user_agent_skills
        except:
            self.agent_skills = None
    
    def get_profile_display(self, user_id: str) -> Dict:
        """Get profile data formatted for display"""
        try:
            # Get base profile
            profile = self.onboarding.get_user_profile(user_id) if self.onboarding else None
            
            if not profile:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Get agent skills
            skills_data = {}
            if self.agent_skills:
                try:
                    skills_data = self.agent_skills.get_user_skills(user_id)
                except:
                    pass
            
            # Get skill stats
            skill_stats = {}
            if self.agent_skills:
                try:
                    skill_stats = self.agent_skills.get_skill_stats(user_id)
                except:
                    pass
            
            # Parse JSON fields
            preferences = {}
            scraped_info = {}
            assigned_agents = []
            
            try:
                if profile.get('preferences'):
                    preferences = json.loads(profile['preferences']) if isinstance(profile['preferences'], str) else profile['preferences']
            except:
                pass
            
            try:
                if profile.get('scraped_info'):
                    scraped_info = json.loads(profile['scraped_info']) if isinstance(profile['scraped_info'], str) else profile['scraped_info']
            except:
                pass
            
            try:
                if profile.get('assigned_agent_ids'):
                    assigned_agents = json.loads(profile['assigned_agent_ids']) if isinstance(profile['assigned_agent_ids'], str) else profile['assigned_agent_ids']
            except:
                pass
            
            # Calculate basic stats
            stats = self._calculate_basic_stats(profile, skills_data, skill_stats)
            
            # Get points data from unified points system
            points_data = {}
            try:
                from backend.services.unified_points_database import unified_points_db
                if unified_points_db:
                    points_result = unified_points_db.get_all_points(user_id)
                    if points_result and isinstance(points_result, dict):
                        points_data = points_result.get('points', points_result.get('all_points', {}))
                        # Add total points to stats
                        if points_data:
                            total_points = sum(v for v in points_data.values() if isinstance(v, (int, float)))
                            stats['total_points'] = total_points
                            # Add specific point types
                            systems = points_data.get('systems') or {}
                            stats['xp_points'] = points_data.get('xp_points', 0) or points_data.get('xp_total', 0)
                            stats['generation_points'] = int(systems.get('generation_points', 0) or points_data.get('generation_points', 0))
                            stats['dna_manipulation_points'] = points_data.get('dna_manipulation_points', 0) or systems.get('dna_manipulation_points', 0)
                            stats['dna_cloning_points'] = points_data.get('dna_cloning_points', 0) or systems.get('dna_cloning_points', 0)
                            stats['communication_psychology_points'] = points_data.get('communication_psychology_points', 0) or systems.get('communication_psychology_points', 0)
                            stats['compendium_points'] = points_data.get('compendium_points', 0) or systems.get('compendium_points', 0)
                            stats['game_points'] = points_data.get('game_points', 0) or systems.get('game_points', 0)
                            stats['game_time_remaining_minutes'] = int(points_data.get('game_time_remaining_minutes', 0) or 0)
                            stats['active_boosters'] = points_data.get('active_boosters') if isinstance(points_data.get('active_boosters'), list) else []
            except Exception as e:
                print(f"Error loading points data: {e}")

            # Star Map 25 (connected to profile point systems)
            try:
                from backend.services.user_account_summary import get_star_map_25_summary
                stats['star_map_25'] = get_star_map_25_summary(user_id)
            except Exception:
                stats['star_map_25'] = {'investigated_count': 0, 'total_points': 25, 'total_points_earned': 0}

            # Communication Psychology — 25 theories progress (for profile display)
            communication_psychology = {}
            try:
                from backend.services.communication_psychology_service import get_user_progress
                cp = get_user_progress(user_id)
                if cp.get('success'):
                    communication_psychology = {
                        'unlocked_count': cp.get('unlocked_count', 0),
                        'total_theories': cp.get('total_theories', 25),
                        'communication_psychology_points': cp.get('communication_psychology_points', 0),
                        'unlocked_theories': cp.get('unlocked_theories', []),
                        'categories': cp.get('categories', []),
                    }
            except Exception:
                pass
            
            return {
                'success': True,
                'profile': {
                    'user_id': profile.get('user_id'),
                    'username': profile.get('username'),
                    'display_name': preferences.get('display_name') or profile.get('username'),
                    'bio': preferences.get('bio', ''),
                    'avatar_url': preferences.get('avatar_url', ''),
                    'join_date': profile.get('created_at'),
                    'onboarding_complete': profile.get('onboarding_complete', False),
                    'skill_path': profile.get('agent_skillset_id', 'balanced'),
                    'assigned_agents': assigned_agents,
                    'preferences': preferences,
                    'scraped_info': scraped_info
                },
                'skills': skills_data,
                'stats': stats,
                'points': points_data,
                'communication_psychology': communication_psychology
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def calculate_profile_stats(self, user_id: str) -> Dict:
        """Calculate comprehensive profile statistics"""
        try:
            profile = self.onboarding.get_user_profile(user_id) if self.onboarding else None
            if not profile:
                return {'success': False, 'error': 'User not found'}
            
            # Get skills data
            skills_data = {}
            skill_stats = {}
            if self.agent_skills:
                try:
                    skills_data = self.agent_skills.get_user_skills(user_id)
                    skill_stats = self.agent_skills.get_skill_stats(user_id)
                except:
                    pass
            
            stats = self._calculate_basic_stats(profile, skills_data, skill_stats)
            
            # Add additional stats
            stats['profile_completion'] = self._calculate_profile_completion(profile)
            stats['activity_score'] = self._calculate_activity_score(profile)
            stats['engagement_level'] = self._calculate_engagement_level(stats)
            
            return {
                'success': True,
                'stats': stats
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_profile_activity(self, user_id: str, limit: int = 10) -> Dict:
        """Get recent profile activity"""
        try:
            # This would typically come from an activity log
            # For now, return placeholder
            return {
                'success': True,
                'activities': [],
                'message': 'Activity tracking coming soon'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_profile_achievements(self, user_id: str) -> Dict:
        """Get user achievements"""
        try:
            # This would typically come from achievement system
            # For now, return placeholder
            return {
                'success': True,
                'achievements': [],
                'message': 'Achievement system integration coming soon'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_basic_stats(self, profile: Dict, skills_data: Dict, skill_stats: Dict) -> Dict:
        """Calculate basic statistics"""
        stats = {
            'total_points': 0,
            'level': 1,
            'experience': 0,
            'achievements_count': 0,
            'skills_count': 0,
            'skills_total_level': 0,
            'average_skill_level': 0
        }
        
        # Get skills count and levels
        if skills_data and isinstance(skills_data, dict):
            skills = skills_data.get('skills', [])
            stats['skills_count'] = len(skills)
            
            if skills:
                total_level = sum(skill.get('level', 1) for skill in skills)
                stats['skills_total_level'] = total_level
                stats['average_skill_level'] = total_level / len(skills) if len(skills) > 0 else 0
        
        # Get skill path
        skill_path = profile.get('agent_skillset_id', 'balanced')
        
        return {
            **stats,
            'skill_path': skill_path,
            'skill_path_name': self._get_skill_path_name(skill_path)
        }
    
    def _calculate_profile_completion(self, profile: Dict) -> float:
        """Calculate profile completion percentage"""
        fields = ['username', 'preferences', 'scraped_info']
        completed = 0
        
        for field in fields:
            if profile.get(field):
                completed += 1
        
        return (completed / len(fields)) * 100
    
    def _calculate_activity_score(self, profile: Dict) -> int:
        """Calculate activity score"""
        # Placeholder - would calculate based on actual activity
        return 50
    
    def _calculate_engagement_level(self, stats: Dict) -> str:
        """Calculate engagement level"""
        score = stats.get('activity_score', 0)
        
        if score >= 80:
            return 'high'
        elif score >= 50:
            return 'medium'
        else:
            return 'low'
    
    def _get_skill_path_name(self, skill_path: str) -> str:
        """Get human-readable skill path name"""
        names = {
            'balanced': 'Balanced',
            'creator': 'Creator',
            'battle': 'Battle Strategist',
            'social': 'Social Player',
            'analytics': 'Analyst'
        }
        return names.get(skill_path, 'Unknown')

# Global instance
user_profile = UserProfile()
