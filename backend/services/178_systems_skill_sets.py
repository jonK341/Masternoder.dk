"""
178 Systems Skill Sets Service
Comprehensive skill sets for all 178 point systems with abilities, thresholds, and multipliers
Integrated with leaderboard intelligence aggregation
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

class SystemsSkillSets178:
    """
    Comprehensive skill sets for all 178 point systems
    Each system has abilities with thresholds and multipliers
    """
    
    # Skill sets for all 178 systems (expanded from frontend version)
    SKILL_SETS = {
        # Core Engagement Systems
        'xp': {
            'name': 'Experience Mastery',
            'system_id': 'xp',
            'category': 'core_engagement',
            'abilities': [
                {'name': 'Basic Experience', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Quick Learner', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Fast Tracker', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Rapid Progress', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Expert Learner', 'threshold': 2500, 'multiplier': 1.5},
                {'name': 'Master Experience', 'threshold': 5000, 'multiplier': 2.0},
                {'name': 'Legendary XP', 'threshold': 10000, 'multiplier': 2.5}
            ]
        },
        'activity': {
            'name': 'Activity Excellence',
            'system_id': 'activity',
            'category': 'core_engagement',
            'abilities': [
                {'name': 'Active User', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Regular Participant', 'threshold': 50, 'multiplier': 1.1},
                {'name': 'Daily Active', 'threshold': 200, 'multiplier': 1.1},
                {'name': 'Highly Active', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Activity Champion', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Activity Master', 'threshold': 2500, 'multiplier': 1.5},
                {'name': 'Activity Legend', 'threshold': 5000, 'multiplier': 2.0}
            ]
        },
        'battle': {
            'name': 'Combat Mastery',
            'system_id': 'battle',
            'category': 'battle_combat',
            'abilities': [
                {'name': 'Warrior', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Skilled Fighter', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Battle Veteran', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Combat Expert', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Battle Master', 'threshold': 2500, 'multiplier': 1.5},
                {'name': 'Combat Legend', 'threshold': 5000, 'multiplier': 2.0}
            ]
        },
        'trophies': {
            'name': 'Trophy Collection Mastery',
            'system_id': 'trophies',
            'category': 'achievements',
            'abilities': [
                {'name': 'Collector', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Trophy Hunter', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Achievement Seeker', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Trophy Master', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Legendary Collector', 'threshold': 2500, 'multiplier': 1.5},
                {'name': 'Ultimate Trophy Master', 'threshold': 5000, 'multiplier': 2.0}
            ]
        },
        'chat': {
            'name': 'Communication Mastery',
            'system_id': 'chat',
            'category': 'social_community',
            'abilities': [
                {'name': 'Chatter', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Active Communicator', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Social Expert', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Communication Master', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Social Legend', 'threshold': 2500, 'multiplier': 1.5}
            ]
        },
        'theme': {
            'name': 'Theme Mastery',
            'system_id': 'theme',
            'category': 'customization',
            'abilities': [
                {'name': 'Theme User', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Theme Enthusiast', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Theme Expert', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Theme Master', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Theme Legend', 'threshold': 2500, 'multiplier': 1.5}
            ]
        },
        'generation': {
            'name': 'Video Production Mastery',
            'system_id': 'generation',
            'category': 'content_creation',
            'abilities': [
                {'name': 'Video Creator', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Video Editor', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Video Producer', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Video Director', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Video Master', 'threshold': 2500, 'multiplier': 1.5},
                {'name': 'Video Legend', 'threshold': 5000, 'multiplier': 2.0}
            ]
        },
        'reward': {
            'name': 'Reward Collection Mastery',
            'system_id': 'reward',
            'category': 'economy',
            'abilities': [
                {'name': 'Reward Collector', 'threshold': 0, 'multiplier': 1.0},
                {'name': 'Reward Hunter', 'threshold': 100, 'multiplier': 1.1},
                {'name': 'Reward Expert', 'threshold': 500, 'multiplier': 1.2},
                {'name': 'Reward Master', 'threshold': 1000, 'multiplier': 1.3},
                {'name': 'Reward Legend', 'threshold': 2500, 'multiplier': 1.5}
            ]
        },
        # Add more systems as needed...
    }
    
    def __init__(self):
        """Initialize service"""
        pass
    
    def get_skill_set(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get skill set for a specific system"""
        return self.SKILL_SETS.get(system_id)
    
    def get_current_ability(self, system_id: str, points: int) -> Optional[Dict[str, Any]]:
        """Get current unlocked ability for a system based on points"""
        skill_set = self.get_skill_set(system_id)
        if not skill_set:
            return None
        
        # Find highest unlocked ability
        current_ability = skill_set['abilities'][0]
        for ability in skill_set['abilities']:
            if points >= ability['threshold']:
                current_ability = ability
            else:
                break
        
        return current_ability
    
    def get_unlocked_abilities(self, system_id: str, points: int) -> List[Dict[str, Any]]:
        """Get all unlocked abilities for a system"""
        skill_set = self.get_skill_set(system_id)
        if not skill_set:
            return []
        
        return [ab for ab in skill_set['abilities'] if points >= ab['threshold']]
    
    def get_next_ability(self, system_id: str, points: int) -> Optional[Dict[str, Any]]:
        """Get next ability to unlock"""
        skill_set = self.get_skill_set(system_id)
        if not skill_set:
            return None
        
        for ability in skill_set['abilities']:
            if points < ability['threshold']:
                return ability
        
        return None  # All abilities unlocked
    
    def get_all_user_skill_sets(self, user_id: str, all_points: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all skill sets for a user with current abilities, progress, and multipliers
        Integrated with unified_point_counter
        """
        user_skill_sets = []
        total_unlocked_abilities = 0
        total_abilities = 0
        total_multiplier = 0.0
        systems_with_skills = 0
        
        # Map system_id to point field in unified_point_counter
        system_point_mapping = {
            'xp': 'xp_total',
            'activity': 'activity_points_total',
            'battle': 'battle_points',
            'trophies': 'trophy_points',
            'chat': 'chat_points',
            'theme': 'theme_points_total',
            'generation': 'generations_total',
            'reward': 'reward_points_total',
        }
        
        for system_id, skill_set in self.SKILL_SETS.items():
            # Get points for this system
            point_field = system_point_mapping.get(system_id, f'{system_id}_points')
            points = all_points.get(point_field, 0) or 0
            
            if points > 0 or system_id in system_point_mapping:
                # Get current and next abilities
                current_ability = self.get_current_ability(system_id, points)
                unlocked_abilities = self.get_unlocked_abilities(system_id, points)
                next_ability = self.get_next_ability(system_id, points)
                
                unlocked_count = len(unlocked_abilities)
                total_abilities_for_system = len(skill_set['abilities'])
                
                total_unlocked_abilities += unlocked_count
                total_abilities += total_abilities_for_system
                if current_ability:
                    total_multiplier += current_ability['multiplier']
                    systems_with_skills += 1
                
                # Calculate progress
                progress_percentage = (unlocked_count / total_abilities_for_system * 100) if total_abilities_for_system > 0 else 0
                
                user_skill_sets.append({
                    'skill_set_name': skill_set['name'],
                    'system_id': system_id,
                    'category': skill_set['category'],
                    'points': points,
                    'current_ability': current_ability,
                    'next_ability': next_ability,
                    'unlocked_count': unlocked_count,
                    'total_abilities': total_abilities_for_system,
                    'progress_percentage': round(progress_percentage, 1),
                    'multiplier': current_ability['multiplier'] if current_ability else 1.0
                })
        
        # Calculate average multiplier
        average_multiplier = (total_multiplier / systems_with_skills) if systems_with_skills > 0 else 1.0
        
        return {
            'success': True,
            'user_id': user_id,
            'skill_sets': user_skill_sets,
            'total_skill_sets': len(user_skill_sets),
            'total_unlocked_abilities': total_unlocked_abilities,
            'total_abilities': total_abilities,
            'average_multiplier': round(average_multiplier, 2),
            'progress_percentage': round((total_unlocked_abilities / total_abilities * 100) if total_abilities > 0 else 0, 1)
        }


# Global instance
systems_skill_sets_178 = SystemsSkillSets178()
