"""
Enhanced Skills System with 10+ New Abilities
Skills walk in pairs of two, connected to quest system
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class EnhancedSkillsSystem:
    """
    Enhanced Skills System with 10+ New Abilities
    - Skills walk in pairs of two
    - Connected to quest system
    - Integrated with point system
    """
    
    # 10+ New Abilities (paired)
    NEW_ABILITIES = [
        # Pair 1: Combat & Defense
        {
            'id': 'dual_wield',
            'name': 'Dual Wield',
            'pair_id': 'combat_pair_1',
            'pair_with': 'defensive_stance',
            'category': 'combat',
            'description': 'Wield two weapons simultaneously',
            'point_value': 50
        },
        {
            'id': 'defensive_stance',
            'name': 'Defensive Stance',
            'pair_id': 'combat_pair_1',
            'pair_with': 'dual_wield',
            'category': 'combat',
            'description': 'Enhanced defensive capabilities',
            'point_value': 50
        },
        # Pair 2: Magic & Technology
        {
            'id': 'arcane_fusion',
            'name': 'Arcane Fusion',
            'pair_id': 'magic_pair_1',
            'pair_with': 'tech_integration',
            'category': 'magic',
            'description': 'Combine magic with technology',
            'point_value': 75
        },
        {
            'id': 'tech_integration',
            'name': 'Tech Integration',
            'pair_id': 'magic_pair_1',
            'pair_with': 'arcane_fusion',
            'category': 'technology',
            'description': 'Integrate technology with magic',
            'point_value': 75
        },
        # Pair 3: Stealth & Detection
        {
            'id': 'shadow_walk',
            'name': 'Shadow Walk',
            'pair_id': 'stealth_pair_1',
            'pair_with': 'detection_mastery',
            'category': 'stealth',
            'description': 'Move undetected through shadows',
            'point_value': 60
        },
        {
            'id': 'detection_mastery',
            'name': 'Detection Mastery',
            'pair_id': 'stealth_pair_1',
            'pair_with': 'shadow_walk',
            'category': 'stealth',
            'description': 'Detect hidden threats and secrets',
            'point_value': 60
        },
        # Pair 4: Creation & Destruction
        {
            'id': 'creative_force',
            'name': 'Creative Force',
            'pair_id': 'creation_pair_1',
            'pair_with': 'destructive_power',
            'category': 'creative',
            'description': 'Unleash creative energies',
            'point_value': 80
        },
        {
            'id': 'destructive_power',
            'name': 'Destructive Power',
            'pair_id': 'creation_pair_1',
            'pair_with': 'creative_force',
            'category': 'combat',
            'description': 'Channel destructive forces',
            'point_value': 80
        },
        # Pair 5: Time & Space
        {
            'id': 'temporal_manipulation',
            'name': 'Temporal Manipulation',
            'pair_id': 'time_pair_1',
            'pair_with': 'spatial_control',
            'category': 'magic',
            'description': 'Control the flow of time',
            'point_value': 100
        },
        {
            'id': 'spatial_control',
            'name': 'Spatial Control',
            'pair_id': 'time_pair_1',
            'pair_with': 'temporal_manipulation',
            'category': 'magic',
            'description': 'Manipulate space and dimensions',
            'point_value': 100
        },
        # Pair 6: Healing & Harm
        {
            'id': 'regenerative_aura',
            'name': 'Regenerative Aura',
            'pair_id': 'healing_pair_1',
            'pair_with': 'toxic_breath',
            'category': 'support',
            'description': 'Restore health over time',
            'point_value': 65
        },
        {
            'id': 'toxic_breath',
            'name': 'Toxic Breath',
            'pair_id': 'healing_pair_1',
            'pair_with': 'regenerative_aura',
            'category': 'combat',
            'description': 'Deal damage over time',
            'point_value': 65
        },
        # Pair 7: Communication & Isolation
        {
            'id': 'telepathic_link',
            'name': 'Telepathic Link',
            'pair_id': 'communication_pair_1',
            'pair_with': 'mind_shield',
            'category': 'social',
            'description': 'Communicate telepathically',
            'point_value': 55
        },
        {
            'id': 'mind_shield',
            'name': 'Mind Shield',
            'pair_id': 'communication_pair_1',
            'pair_with': 'telepathic_link',
            'category': 'defense',
            'description': 'Protect from mental attacks',
            'point_value': 55
        },
        # Pair 8: Growth & Decay
        {
            'id': 'growth_acceleration',
            'name': 'Growth Acceleration',
            'pair_id': 'growth_pair_1',
            'pair_with': 'decay_aura',
            'category': 'nature',
            'description': 'Accelerate growth and development',
            'point_value': 70
        },
        {
            'id': 'decay_aura',
            'name': 'Decay Aura',
            'pair_id': 'growth_pair_1',
            'pair_with': 'growth_acceleration',
            'category': 'nature',
            'description': 'Cause decay and deterioration',
            'point_value': 70
        },
        # Pair 9: Light & Dark
        {
            'id': 'light_manifestation',
            'name': 'Light Manifestation',
            'pair_id': 'light_pair_1',
            'pair_with': 'dark_embrace',
            'category': 'magic',
            'description': 'Create and control light',
            'point_value': 85
        },
        {
            'id': 'dark_embrace',
            'name': 'Dark Embrace',
            'pair_id': 'light_pair_1',
            'pair_with': 'light_manifestation',
            'category': 'magic',
            'description': 'Channel dark energies',
            'point_value': 85
        },
        # Pair 10: Speed & Strength
        {
            'id': 'speed_boost',
            'name': 'Speed Boost',
            'pair_id': 'speed_pair_1',
            'pair_with': 'strength_amplification',
            'category': 'physical',
            'description': 'Increase movement and reaction speed',
            'point_value': 45
        },
        {
            'id': 'strength_amplification',
            'name': 'Strength Amplification',
            'pair_id': 'speed_pair_1',
            'pair_with': 'speed_boost',
            'category': 'physical',
            'description': 'Increase physical strength',
            'point_value': 45
        }
    ]
    
    def __init__(self):
        self.user_abilities = defaultdict(dict)  # {user_id: {ability_id: ability_data}}
        self.ability_pairs = defaultdict(list)  # {user_id: [pair_ids]}
        
    def get_all_abilities(self) -> Dict[str, Any]:
        """Get all available abilities"""
        return {
            'success': True,
            'abilities': self.NEW_ABILITIES,
            'total_abilities': len(self.NEW_ABILITIES),
            'total_pairs': len(self.NEW_ABILITIES) // 2
        }
    
    def unlock_ability(self, user_id: str, ability_id: str, quest_id: Optional[str] = None) -> Dict[str, Any]:
        """Unlock an ability (may require quest completion)"""
        # Find ability
        ability = None
        for ab in self.NEW_ABILITIES:
            if ab['id'] == ability_id:
                ability = ab
                break
        
        if not ability:
            return {'success': False, 'error': 'Ability not found'}
        
        # Check if already unlocked
        if ability_id in self.user_abilities.get(user_id, {}):
            return {'success': False, 'error': 'Ability already unlocked'}
        
        # Unlock ability
        self.user_abilities[user_id][ability_id] = {
            **ability,
            'unlocked_at': datetime.utcnow().isoformat(),
            'quest_id': quest_id,
            'level': 1,
            'experience': 0
        }
        
        # Check if pair should be unlocked
        pair_with = ability.get('pair_with')
        if pair_with:
            pair_id = ability.get('pair_id')
            if pair_id not in self.ability_pairs[user_id]:
                self.ability_pairs[user_id].append(pair_id)
        
        # Award points
        if point_connection:
            try:
                point_connection.ensure_point_counting(
                    user_id,
                    'ability_points',
                    ability.get('point_value', 50),
                    'enhanced_skills_system'
                )
            except Exception as e:
                print(f"[EnhancedSkills] Error awarding points: {e}")
        
        return {
            'success': True,
            'ability_id': ability_id,
            'ability_name': ability.get('name'),
            'pair_id': ability.get('pair_id'),
            'points_awarded': ability.get('point_value', 50)
        }
    
    def unlock_ability_pair(self, user_id: str, pair_id: str) -> Dict[str, Any]:
        """Unlock both abilities in a pair"""
        # Find abilities in pair
        pair_abilities = [ab for ab in self.NEW_ABILITIES if ab.get('pair_id') == pair_id]
        
        if not pair_abilities:
            return {'success': False, 'error': 'Pair not found'}
        
        unlocked = []
        for ability in pair_abilities:
            if ability['id'] not in self.user_abilities.get(user_id, {}):
                result = self.unlock_ability(user_id, ability['id'])
                if result.get('success'):
                    unlocked.append(ability['id'])
        
        return {
            'success': True,
            'pair_id': pair_id,
            'unlocked_abilities': unlocked,
            'total_unlocked': len(unlocked)
        }
    
    def get_user_abilities(self, user_id: str) -> Dict[str, Any]:
        """Get user's unlocked abilities"""
        user_abilities = self.user_abilities.get(user_id, {})
        pairs = self.ability_pairs.get(user_id, [])
        
        return {
            'success': True,
            'user_id': user_id,
            'abilities': list(user_abilities.values()),
            'unlocked_count': len(user_abilities),
            'pairs_unlocked': len(pairs),
            'total_available': len(self.NEW_ABILITIES)
        }


# Global instance
enhanced_skills_system = EnhancedSkillsSystem()

