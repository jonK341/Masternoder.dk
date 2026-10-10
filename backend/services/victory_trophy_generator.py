"""
Victory Trophy Generator
Generates resources and victory trophies for top performers
"""
from typing import Dict, List, Any
from datetime import datetime
from decimal import Decimal
import uuid

class VictoryTrophyGenerator:
    """
    Victory Trophy and Resource Generation System
    For top 6 performers and achievements
    """
    
    def __init__(self):
        self.trophy_types = {
            'gold_champion': {
                'name': 'Gold Champion',
                'rank_required': 1,
                'resources': {'cash': 1000, 'energy_mind': 50, 'energy_power': 50},
                'trophy_value': 10000
            },
            'silver_elite': {
                'name': 'Silver Elite',
                'rank_required': 2,
                'resources': {'cash': 750, 'energy_mind': 40, 'energy_power': 40},
                'trophy_value': 7500
            },
            'bronze_warrior': {
                'name': 'Bronze Warrior',
                'rank_required': 3,
                'resources': {'cash': 500, 'energy_mind': 30, 'energy_power': 30},
                'trophy_value': 5000
            },
            'platinum_master': {
                'name': 'Platinum Master',
                'rank_required': 4,
                'resources': {'cash': 400, 'energy_mind': 25, 'energy_power': 25},
                'trophy_value': 4000
            },
            'diamond_legend': {
                'name': 'Diamond Legend',
                'rank_required': 5,
                'resources': {'cash': 300, 'energy_mind': 20, 'energy_power': 20},
                'trophy_value': 3000
            },
            'crystal_hero': {
                'name': 'Crystal Hero',
                'rank_required': 6,
                'resources': {'cash': 200, 'energy_mind': 15, 'energy_power': 15},
                'trophy_value': 2000
            }
        }
        
        self.user_trophies = {}  # user_id -> [trophies]
        self.resource_rewards = {}  # user_id -> [rewards]
    
    def generate_trophy_for_rank(self, user_id: str, rank: int) -> Dict[str, Any]:
        """Generate trophy and resources for rank"""
        trophy_type = None
        
        for trophy_id, trophy_config in self.trophy_types.items():
            if trophy_config['rank_required'] == rank:
                trophy_type = trophy_id
                break
        
        if not trophy_type:
            return {'success': False, 'error': 'No trophy for this rank'}
        
        trophy_config = self.trophy_types[trophy_type]
        
        # Create trophy
        trophy = {
            'trophy_id': str(uuid.uuid4()),
            'user_id': user_id,
            'trophy_type': trophy_type,
            'trophy_name': trophy_config['name'],
            'rank': rank,
            'resources': trophy_config['resources'],
            'trophy_value': trophy_config['trophy_value'],
            'awarded_at': datetime.utcnow().isoformat()
        }
        
        # Store trophy
        if user_id not in self.user_trophies:
            self.user_trophies[user_id] = []
        self.user_trophies[user_id].append(trophy)
        
        # Generate resources
        resources = self._generate_resources(user_id, trophy_config['resources'])
        
        return {
            'success': True,
            'trophy': trophy,
            'resources': resources,
            'message': f'Awarded {trophy_config["name"]} trophy and resources!'
        }
    
    def _generate_resources(self, user_id: str, resource_config: Dict) -> Dict[str, Any]:
        """Generate resources for user"""
        if user_id not in self.resource_rewards:
            self.resource_rewards[user_id] = []
        
        reward = {
            'reward_id': str(uuid.uuid4()),
            'user_id': user_id,
            'resources': resource_config,
            'awarded_at': datetime.utcnow().isoformat()
        }
        
        self.resource_rewards[user_id].append(reward)
        
        return reward
    
    def get_user_trophies(self, user_id: str) -> Dict[str, Any]:
        """Get user trophies"""
        trophies = self.user_trophies.get(user_id, [])
        
        return {
            'success': True,
            'user_id': user_id,
            'trophies': trophies,
            'total_trophies': len(trophies),
            'total_trophy_value': sum([t.get('trophy_value', 0) for t in trophies])
        }
    
    def get_top_6_trophies(self, top_6_users: List[Dict]) -> Dict[str, Any]:
        """Get trophies for top 6 users"""
        top_6_trophies = {}
        
        for user in top_6_users:
            user_id = user['user_id']
            rank = user['rank']
            
            # Generate trophy if not exists
            trophy_result = self.generate_trophy_for_rank(user_id, rank)
            if trophy_result['success']:
                top_6_trophies[user_id] = {
                    'rank': rank,
                    'trophy': trophy_result['trophy'],
                    'resources': trophy_result['resources']
                }
        
        return {
            'success': True,
            'top_6_trophies': top_6_trophies,
            'generated_at': datetime.utcnow().isoformat()
        }

# Global instance
victory_trophy_generator = VictoryTrophyGenerator()

