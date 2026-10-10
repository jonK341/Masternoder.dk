"""
Graduation Points System
Awards graduation points at level milestones and upgrades
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import json

try:
    from src.services.behavioral_tracking.xp_system import XPSystem
    xp_system = XPSystem()
except ImportError:
    xp_system = None

try:
    from src.services.behavioral_tracking.trophy_system import TrophySystem
    trophy_system = TrophySystem()
except ImportError:
    trophy_system = None


class GraduationPointsSystem:
    """Manages graduation points awarded at milestones and upgrades"""
    
    def __init__(self):
        self.milestone_rewards = self._initialize_milestone_rewards()
        self.upgrade_rewards = self._initialize_upgrade_rewards()
    
    def _initialize_milestone_rewards(self) -> Dict[int, Dict[str, Any]]:
        """Initialize graduation points for level milestones"""
        return {
            5: {'graduation_points': 10, 'title': 'Apprentice', 'description': 'Reached level 5'},
            10: {'graduation_points': 25, 'title': 'Journeyman', 'description': 'Reached level 10'},
            15: {'graduation_points': 50, 'title': 'Expert', 'description': 'Reached level 15'},
            20: {'graduation_points': 100, 'title': 'Master', 'description': 'Reached level 20'},
            25: {'graduation_points': 200, 'title': 'Grandmaster', 'description': 'Reached level 25'},
            30: {'graduation_points': 300, 'title': 'Legend', 'description': 'Reached level 30'},
            40: {'graduation_points': 500, 'title': 'Mythic', 'description': 'Reached level 40'},
            50: {'graduation_points': 1000, 'title': 'Transcendent', 'description': 'Reached level 50'},
            75: {'graduation_points': 2000, 'title': 'Divine', 'description': 'Reached level 75'},
            100: {'graduation_points': 5000, 'title': 'Immortal', 'description': 'Reached level 100'}
        }
    
    def _initialize_upgrade_rewards(self) -> Dict[str, Dict[str, Any]]:
        """Initialize graduation points for subscription upgrades"""
        return {
            'free_to_pro': {'graduation_points': 50, 'description': 'Upgraded to Pro'},
            'pro_to_business': {'graduation_points': 200, 'description': 'Upgraded to Business'},
            'business_to_enterprise': {'graduation_points': 500, 'description': 'Upgraded to Enterprise'},
            'any_upgrade': {'graduation_points': 25, 'description': 'Any subscription upgrade'}
        }
    
    def check_milestone_graduation(self, user_id: str, level: int) -> Optional[Dict[str, Any]]:
        """Check if user reached a milestone and award graduation points"""
        if level not in self.milestone_rewards:
            return None
        
        if not xp_system:
            return None
        
        try:
            profile = xp_system.get_user_profile(user_id)
            knowledge = profile.get('knowledge', {})
            completed_milestones = knowledge.get('graduation_milestones', [])
            
            # Check if already awarded
            if level in completed_milestones:
                return None
            
            milestone = self.milestone_rewards[level]
            
            # Award graduation points
            current_points = knowledge.get('graduation_points', 0)
            new_points = current_points + milestone['graduation_points']
            
            # Update knowledge
            if 'graduation_milestones' not in knowledge:
                knowledge['graduation_milestones'] = []
            knowledge['graduation_milestones'].append(level)
            knowledge['graduation_points'] = new_points
            knowledge['total_graduation_points_earned'] = knowledge.get('total_graduation_points_earned', 0) + milestone['graduation_points']
            
            # Save updated profile
            xp_system.save_user_profile(user_id, profile)
            
            print(f"[GraduationPoints] User {user_id} reached level {level} milestone: {milestone['title']}")
            print(f"[GraduationPoints] Awarded {milestone['graduation_points']} graduation points (total: {new_points})")
            
            return {
                'milestone_level': level,
                'title': milestone['title'],
                'description': milestone['description'],
                'graduation_points_awarded': milestone['graduation_points'],
                'total_graduation_points': new_points
            }
        except Exception as e:
            print(f"[GraduationPoints] Error checking milestone: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def check_upgrade_graduation(self, user_id: str, old_tier: str, new_tier: str) -> Optional[Dict[str, Any]]:
        """Check if user upgraded and award graduation points"""
        if old_tier == new_tier:
            return None
        
        upgrade_key = f"{old_tier}_to_{new_tier}"
        upgrade_reward = self.upgrade_rewards.get(upgrade_key) or self.upgrade_rewards.get('any_upgrade')
        
        if not upgrade_reward or not xp_system:
            return None
        
        try:
            profile = xp_system.get_user_profile(user_id)
            knowledge = profile.get('knowledge', {})
            
            # Award graduation points
            current_points = knowledge.get('graduation_points', 0)
            new_points = current_points + upgrade_reward['graduation_points']
            
            knowledge['graduation_points'] = new_points
            knowledge['total_graduation_points_earned'] = knowledge.get('total_graduation_points_earned', 0) + upgrade_reward['graduation_points']
            knowledge['upgrade_history'] = knowledge.get('upgrade_history', [])
            knowledge['upgrade_history'].append({
                'from': old_tier,
                'to': new_tier,
                'points_awarded': upgrade_reward['graduation_points'],
                'timestamp': datetime.now().isoformat()
            })
            
            # Save updated profile
            xp_system.save_user_profile(user_id, profile)
            
            print(f"[GraduationPoints] User {user_id} upgraded from {old_tier} to {new_tier}")
            print(f"[GraduationPoints] Awarded {upgrade_reward['graduation_points']} graduation points (total: {new_points})")
            
            return {
                'upgrade_from': old_tier,
                'upgrade_to': new_tier,
                'graduation_points_awarded': upgrade_reward['graduation_points'],
                'total_graduation_points': new_points,
                'description': upgrade_reward['description']
            }
        except Exception as e:
            print(f"[GraduationPoints] Error checking upgrade: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_graduation_points(self, user_id: str) -> Dict[str, Any]:
        """Get user's graduation points and milestones"""
        if not xp_system:
            return {'graduation_points': 0, 'milestones': []}
        
        try:
            profile = xp_system.get_user_profile(user_id)
            knowledge = profile.get('knowledge', {})
            
            completed_milestones = knowledge.get('graduation_milestones', [])
            milestones = []
            
            for level, milestone_data in sorted(self.milestone_rewards.items()):
                is_completed = level in completed_milestones
                milestones.append({
                    'level': level,
                    'title': milestone_data['title'],
                    'description': milestone_data['description'],
                    'points': milestone_data['graduation_points'],
                    'completed': is_completed
                })
            
            return {
                'graduation_points': knowledge.get('graduation_points', 0),
                'total_earned': knowledge.get('total_graduation_points_earned', 0),
                'milestones': milestones,
                'completed_count': len(completed_milestones),
                'total_milestones': len(self.milestone_rewards)
            }
        except Exception as e:
            print(f"[GraduationPoints] Error getting points: {e}")
            return {'graduation_points': 0, 'milestones': []}


# Global instance
graduation_points_system = GraduationPointsSystem()

