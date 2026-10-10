"""
Skills and Abilities Tracker
Tracks all skills and abilities with aggregator resources
Integrates with unified point system
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class SkillsAbilitiesTracker:
    """
    Tracks skills and abilities with aggregator resources
    All skills count towards unified point system
    """
    
    def __init__(self):
        self.skills = {}
        self.abilities = {}
        self.aggregator_resources = {}
        self.skill_categories = {
            'combat': ['strength', 'defense', 'speed', 'agility'],
            'magic': ['spell_power', 'mana', 'intelligence', 'wisdom'],
            'tech': ['programming', 'hardware', 'networking', 'ai'],
            'social': ['charisma', 'leadership', 'negotiation', 'diplomacy'],
            'creative': ['art', 'music', 'writing', 'design'],
            'physical': ['endurance', 'flexibility', 'coordination', 'balance']
        }
    
    def update_skill(self, user_id: str, skill_category: str, skill_name: str, 
                    value: float, source: str = 'default'):
        """Update a skill with aggregator resource tracking"""
        if user_id not in self.skills:
            self.skills[user_id] = {}
        if skill_category not in self.skills[user_id]:
            self.skills[user_id][skill_category] = {}
        if skill_name not in self.skills[user_id][skill_category]:
            self.skills[user_id][skill_category][skill_name] = {
                'value': 0.0,
                'sources': {},
                'last_updated': None
            }
        
        self.skills[user_id][skill_category][skill_name]['value'] += value
        if source not in self.skills[user_id][skill_category][skill_name]['sources']:
            self.skills[user_id][skill_category][skill_name]['sources'][source] = 0.0
        self.skills[user_id][skill_category][skill_name]['sources'][source] += value
        self.skills[user_id][skill_category][skill_name]['last_updated'] = datetime.utcnow().isoformat()
        
        # Update aggregator resources
        self._update_aggregator_resource(user_id, skill_category, skill_name, value)
        
        # Count towards unified point system
        self._count_towards_unified_points(user_id, skill_category, skill_name, value)
    
    def update_ability(self, user_id: str, ability_name: str, value: float, 
                     source: str = 'default'):
        """Update an ability with aggregator resource tracking"""
        if user_id not in self.abilities:
            self.abilities[user_id] = {}
        if ability_name not in self.abilities[user_id]:
            self.abilities[user_id][ability_name] = {
                'value': 0.0,
                'sources': {},
                'last_updated': None
            }
        
        self.abilities[user_id][ability_name]['value'] += value
        if source not in self.abilities[user_id][ability_name]['sources']:
            self.abilities[user_id][ability_name]['sources'][source] = 0.0
        self.abilities[user_id][ability_name]['sources'][source] += value
        self.abilities[user_id][ability_name]['last_updated'] = datetime.utcnow().isoformat()
        
        # Count towards unified point system
        self._count_towards_unified_points(user_id, 'ability', ability_name, value)
    
    def _update_aggregator_resource(self, user_id: str, category: str, 
                                   skill_name: str, value: float):
        """Update aggregator resources"""
        if user_id not in self.aggregator_resources:
            self.aggregator_resources[user_id] = {}
        
        resource_key = f"{category}_{skill_name}"
        if resource_key not in self.aggregator_resources[user_id]:
            self.aggregator_resources[user_id][resource_key] = {
                'total': 0.0,
                'count': 0,
                'average': 0.0
            }
        
        resource = self.aggregator_resources[user_id][resource_key]
        resource['total'] += value
        resource['count'] += 1
        resource['average'] = resource['total'] / resource['count']
    
    def _count_towards_unified_points(self, user_id: str, category: str, 
                                     name: str, value: float):
        """Count skill/ability towards unified point system"""
        # This would integrate with unified point counter
        try:
            from backend.middleware.intelligent_point_middleware import intelligent_point_middleware
            intelligent_point_middleware.process_point_update(
                user_id, 
                f"skill_{category}_{name}",
                value,
                {'type': 'skill', 'category': category, 'name': name}
            )
        except Exception as e:
            logger.warning(f"Failed to count skill towards unified points: {e}")
    
    def get_all_skills_abilities(self, user_id: str) -> Dict[str, Any]:
        """Get all skills and abilities for user"""
        return {
            'skills': self.skills.get(user_id, {}),
            'abilities': self.abilities.get(user_id, {}),
            'aggregator_resources': self.aggregator_resources.get(user_id, {}),
            'total_skill_points': self._calculate_total_skill_points(user_id),
            'total_ability_points': self._calculate_total_ability_points(user_id)
        }
    
    def _calculate_total_skill_points(self, user_id: str) -> float:
        """Calculate total skill points"""
        total = 0.0
        user_skills = self.skills.get(user_id, {})
        for category, skills in user_skills.items():
            for skill_name, skill_data in skills.items():
                total += skill_data.get('value', 0.0)
        return total
    
    def _calculate_total_ability_points(self, user_id: str) -> float:
        """Calculate total ability points"""
        total = 0.0
        user_abilities = self.abilities.get(user_id, {})
        for ability_name, ability_data in user_abilities.items():
            total += ability_data.get('value', 0.0)
        return total

# Global instance
skills_abilities_tracker = SkillsAbilitiesTracker()

