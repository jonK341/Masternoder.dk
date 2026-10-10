"""
Agent Battle Skills System
Battle skills specifically for agents
"""
from typing import Dict, Any, List
from collections import defaultdict

class AgentBattleSkills:
    """Battle skills specifically for agents"""
    
    BATTLE_SKILLS = [
        {
            'id': 'berserker_rage',
            'name': 'Berserker Rage',
            'category': 'combat',
            'type': 'offensive',
            'description': 'Unleash devastating attacks with increased damage',
            'base_damage_bonus': 25,
            'point_value': 100,
            'unlock_level': 5,
            'icon': '⚔️'
        },
        {
            'id': 'shield_bash',
            'name': 'Shield Bash',
            'category': 'combat',
            'type': 'defensive_offensive',
            'description': 'Bash enemies while protecting yourself',
            'base_damage_bonus': 15,
            'defense_bonus': 20,
            'point_value': 80,
            'unlock_level': 3,
            'icon': '🛡️'
        },
    ]
    
    def __init__(self):
        self.user_skills = defaultdict(dict)  # {user_id: {skill_id: skill_data}}
    
    def get_all_battle_skills(self) -> Dict[str, Any]:
        """Get all available battle skills"""
        return {
            'success': True,
            'skills': self.BATTLE_SKILLS,
            'total': len(self.BATTLE_SKILLS)
        }
    
    def unlock_skill(self, user_id: str, skill_id: str) -> Dict[str, Any]:
        """Unlock a battle skill for a user"""
        skill = next((s for s in self.BATTLE_SKILLS if s['id'] == skill_id), None)
        if not skill:
            return {'success': False, 'error': 'Skill not found'}
        
        if skill_id not in self.user_skills[user_id]:
            self.user_skills[user_id][skill_id] = {
                **skill,
                'unlocked': True,
                'level': 1,
                'xp': 0
            }
            return {'success': True, 'skill': self.user_skills[user_id][skill_id]}
        return {'success': False, 'error': 'Skill already unlocked'}
    
    def get_user_skills(self, user_id: str) -> Dict[str, Any]:
        """Get all unlocked battle skills for a user"""
        return {
            'success': True,
            'user_id': user_id,
            'skills': list(self.user_skills[user_id].values()),
            'total': len(self.user_skills[user_id])
        }
    
    def level_up_skill(self, user_id: str, skill_id: str, xp_gained: int) -> Dict[str, Any]:
        """Level up a battle skill"""
        if skill_id not in self.user_skills[user_id]:
            return {'success': False, 'error': 'Skill not unlocked'}
        
        skill = self.user_skills[user_id][skill_id]
        skill['xp'] = skill.get('xp', 0) + xp_gained
        
        # Level up every 100 XP
        new_level = (skill['xp'] // 100) + 1
        if new_level > skill.get('level', 1):
            skill['level'] = new_level
        
        return {'success': True, 'skill': skill}

agent_battle_skills = AgentBattleSkills()
