"""
Trophy System
New trophy types: win_trophy, victory_trophies, killer_trophies, familie_shield_trophies
"""
from typing import Dict, Any, List
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class TrophySystem:
    """Manages trophy awards and tracking"""
    
    def __init__(self):
        self.trophy_definitions = {
            'win_trophy': {
                'name': 'Win Trophy',
                'description': 'Awarded for battle victories',
                'point_value': 50,
                'requirements': {'battle_victories': 1},
                'category': 'battle'
            },
            'victory_trophies': {
                'name': 'Victory Trophies',
                'description': 'Multiple victory achievements',
                'point_value': 100,
                'requirements': {'battle_victories': 10},
                'category': 'battle',
                'tiers': [
                    {'name': 'Bronze Victory', 'victories': 10, 'points': 100},
                    {'name': 'Silver Victory', 'victories': 50, 'points': 250},
                    {'name': 'Gold Victory', 'victories': 100, 'points': 500},
                    {'name': 'Platinum Victory', 'victories': 250, 'points': 1000},
                    {'name': 'Diamond Victory', 'victories': 500, 'points': 2500}
                ]
            },
            'killer_trophies': {
                'name': 'Killer Trophies',
                'description': 'Combat excellence awards',
                'point_value': 200,
                'requirements': {'kills': 10},
                'category': 'battle',
                'tiers': [
                    {'name': 'Novice Killer', 'kills': 10, 'points': 200},
                    {'name': 'Skilled Killer', 'kills': 50, 'points': 500},
                    {'name': 'Expert Killer', 'kills': 100, 'points': 1000},
                    {'name': 'Master Killer', 'kills': 250, 'points': 2500},
                    {'name': 'Legendary Killer', 'kills': 500, 'points': 5000}
                ]
            },
            'familie_shield_trophies': {
                'name': 'Familie Shield Trophies',
                'description': 'Family/team protection awards',
                'point_value': 150,
                'requirements': {'family_protections': 5},
                'category': 'social',
                'tiers': [
                    {'name': 'Family Protector', 'protections': 5, 'points': 150},
                    {'name': 'Shield Bearer', 'protections': 25, 'points': 500},
                    {'name': 'Guardian', 'protections': 50, 'points': 1000},
                    {'name': 'Defender', 'protections': 100, 'points': 2000},
                    {'name': 'Ultimate Shield', 'protections': 250, 'points': 5000}
                ]
            }
        }
        
        self.user_trophies = {}  # user_id -> [trophy_ids]
    
    def award_trophy(self, user_id: str, trophy_type: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Award a trophy to a user"""
        if trophy_type not in self.trophy_definitions:
            return {'success': False, 'error': 'Trophy type not found'}
        
        trophy_def = self.trophy_definitions[trophy_type]
        metadata = metadata or {}
        
        # Check if user already has this trophy
        if user_id not in self.user_trophies:
            self.user_trophies[user_id] = []
        
        if trophy_type in self.user_trophies[user_id]:
            return {'success': False, 'error': 'Trophy already awarded'}
        
        # Award trophy
        self.user_trophies[user_id].append(trophy_type)
        
        # Award points
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                user_id,
                'trophy',
                trophy_def['point_value'],
                source='trophy_award'
            )
        except Exception as e:
            logger.error(f"Error awarding trophy points: {e}")
        
        return {
            'success': True,
            'trophy_type': trophy_type,
            'trophy_name': trophy_def['name'],
            'points_awarded': trophy_def['point_value'],
            'user_id': user_id
        }
    
    def check_tier_progression(self, user_id: str, trophy_type: str, current_value: int) -> Dict[str, Any]:
        """Check if user qualifies for next trophy tier"""
        if trophy_type not in self.trophy_definitions:
            return {'success': False, 'error': 'Trophy type not found'}
        
        trophy_def = self.trophy_definitions[trophy_type]
        if 'tiers' not in trophy_def:
            return {'success': False, 'error': 'No tiers defined for this trophy'}
        
        # Find current tier
        current_tier = None
        next_tier = None
        
        for tier in trophy_def['tiers']:
            requirement_key = list(trophy_def['requirements'].keys())[0]
            requirement_value = tier.get(requirement_key.replace('_', ''), tier.get(list(tier.keys())[1]))
            
            if current_value >= requirement_value:
                current_tier = tier
            elif next_tier is None and current_value < requirement_value:
                next_tier = tier
                break
        
        return {
            'success': True,
            'current_tier': current_tier,
            'next_tier': next_tier,
            'progress': current_value,
            'unlocked': current_tier is not None
        }
    
    def get_user_trophies(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all trophies for a user"""
        user_trophy_ids = self.user_trophies.get(user_id, [])
        trophies = []
        
        for trophy_id in user_trophy_ids:
            if trophy_id in self.trophy_definitions:
                trophies.append({
                    'id': trophy_id,
                    **self.trophy_definitions[trophy_id]
                })
        
        return trophies

trophy_system = TrophySystem()
