"""
Skill Reward System - Extra Mechanic Skill Each Finish
Rewards users with skills when they complete tasks
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.enhanced_skills_system import enhanced_skills_system
    from backend.services.point_connection_system import PointConnectionSystem
    point_connection = PointConnectionSystem()
except ImportError:
    enhanced_skills_system = None
    point_connection = None


class SkillRewardSystem:
    """
    Skill Reward System
    - Awards extra mechanic skills when tasks are completed
    - Tracks completion milestones
    - Unlocks abilities based on completion count
    """
    
    # Skill rewards based on completion milestones
    COMPLETION_SKILL_REWARDS = {
        1: {'skill_type': 'basic_mechanic', 'skill_name': 'Task Master', 'point_value': 25},
        5: {'skill_type': 'intermediate_mechanic', 'skill_name': 'Completion Expert', 'point_value': 50},
        10: {'skill_type': 'advanced_mechanic', 'skill_name': 'Finisher Pro', 'point_value': 100},
        25: {'skill_type': 'expert_mechanic', 'skill_name': 'Completion Master', 'point_value': 200},
        50: {'skill_type': 'master_mechanic', 'skill_name': 'Grand Finisher', 'point_value': 500},
        100: {'skill_type': 'legendary_mechanic', 'skill_name': 'Completion Legend', 'point_value': 1000}
    }
    
    def __init__(self):
        self.user_completions = defaultdict(int)  # {user_id: completion_count}
        self.completion_history = defaultdict(list)  # {user_id: [completion_data]}
        self.rewarded_milestones = defaultdict(set)  # {user_id: {milestone_numbers}}
    
    def record_completion(self, user_id: str, task_type: str, task_id: str, 
                         completion_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Record a task completion and award skill if milestone reached"""
        # Increment completion count
        self.user_completions[user_id] += 1
        completion_count = self.user_completions[user_id]
        
        # Record completion
        completion_record = {
            'task_id': task_id,
            'task_type': task_type,
            'completed_at': datetime.utcnow().isoformat(),
            'completion_number': completion_count,
            'completion_data': completion_data or {}
        }
        self.completion_history[user_id].append(completion_record)
        
        # Check for milestone rewards
        reward_awarded = None
        for milestone, reward_data in self.COMPLETION_SKILL_REWARDS.items():
            if completion_count == milestone and milestone not in self.rewarded_milestones[user_id]:
                reward_awarded = self._award_milestone_skill(user_id, milestone, reward_data)
                self.rewarded_milestones[user_id].add(milestone)
                break
        
        return {
            'success': True,
            'user_id': user_id,
            'completion_count': completion_count,
            'reward_awarded': reward_awarded,
            'next_milestone': self._get_next_milestone(completion_count)
        }
    
    def _award_milestone_skill(self, user_id: str, milestone: int, reward_data: Dict[str, Any]) -> Dict[str, Any]:
        """Award skill for reaching milestone"""
        skill_id = f"completion_milestone_{milestone}"
        skill_name = reward_data.get('skill_name', f'Milestone {milestone} Skill')
        
        # Award points
        if point_connection:
            try:
                point_connection.ensure_point_counting(
                    user_id,
                    'skill_reward_points',
                    reward_data.get('point_value', 0),
                    'skill_reward_system'
                )
            except Exception as e:
                print(f"[SkillReward] Error awarding points: {e}")
        
        # Try to unlock ability if enhanced skills system available
        if enhanced_skills_system:
            try:
                # Find a suitable ability to unlock
                abilities = enhanced_skills_system.get_all_abilities()
                if abilities.get('success') and abilities.get('abilities'):
                    # Unlock a random ability as reward (or first available)
                    available_abilities = [ab for ab in abilities['abilities'] 
                                         if ab['id'] not in enhanced_skills_system.user_abilities.get(user_id, {})]
                    if available_abilities:
                        ability_to_unlock = available_abilities[0]
                        enhanced_skills_system.unlock_ability(user_id, ability_to_unlock['id'])
            except Exception as e:
                print(f"[SkillReward] Error unlocking ability: {e}")
        
        return {
            'milestone': milestone,
            'skill_name': skill_name,
            'skill_type': reward_data.get('skill_type'),
            'points_awarded': reward_data.get('point_value', 0),
            'skill_id': skill_id
        }
    
    def _get_next_milestone(self, current_count: int) -> Optional[int]:
        """Get next milestone"""
        milestones = sorted(self.COMPLETION_SKILL_REWARDS.keys())
        for milestone in milestones:
            if milestone > current_count:
                return milestone
        return None
    
    def get_user_completions(self, user_id: str) -> Dict[str, Any]:
        """Get user's completion stats"""
        completion_count = self.user_completions.get(user_id, 0)
        history = self.completion_history.get(user_id, [])
        rewarded = list(self.rewarded_milestones.get(user_id, set()))
        next_milestone = self._get_next_milestone(completion_count)
        
        return {
            'success': True,
            'user_id': user_id,
            'total_completions': completion_count,
            'milestones_reached': rewarded,
            'next_milestone': next_milestone,
            'completion_history': history[-10:] if len(history) > 10 else history  # Last 10
        }


# Global instance
skill_reward_system = SkillRewardSystem()

