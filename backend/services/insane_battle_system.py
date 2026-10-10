"""
Insane Battle System
Advanced battle mechanics with extreme difficulty levels
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
from decimal import Decimal
import uuid
import random

class InsaneBattleSystem:
    """
    Insane Battle System
    Extreme difficulty battles with advanced mechanics
    """
    
    def __init__(self):
        self.battle_types = {
            'insane_lock': {
                'name': 'Insane Lock Battle',
                'difficulty': 'extreme',
                'base_reward': Decimal('100.0'),
                'energy_cost': {'mind': 50, 'power': 50},
                'description': 'Extreme difficulty battle with locked mechanics'
            },
            'ultimate_challenge': {
                'name': 'Ultimate Challenge',
                'difficulty': 'extreme',
                'base_reward': Decimal('150.0'),
                'energy_cost': {'mind': 60, 'power': 60},
                'description': 'Ultimate challenge battle'
            },
            'death_match': {
                'name': 'Death Match',
                'difficulty': 'extreme',
                'base_reward': Decimal('200.0'),
                'energy_cost': {'mind': 70, 'power': 70},
                'description': 'Fight to the death - extreme battle'
            },
            'survival_mode': {
                'name': 'Survival Mode',
                'difficulty': 'extreme',
                'base_reward': Decimal('250.0'),
                'energy_cost': {'mind': 80, 'power': 80},
                'description': 'Survive as long as possible'
            },
            'boss_raid': {
                'name': 'Boss Raid',
                'difficulty': 'extreme',
                'base_reward': Decimal('300.0'),
                'energy_cost': {'mind': 90, 'power': 90},
                'description': 'Raid against powerful boss'
            },
            'final_stand': {
                'name': 'Final Stand',
                'difficulty': 'extreme',
                'base_reward': Decimal('500.0'),
                'energy_cost': {'mind': 100, 'power': 100},
                'description': 'Final stand - maximum difficulty'
            }
        }
        
        self.active_battles = {}  # battle_id -> battle_data
        self.battle_history = {}  # user_id -> [battle_results]
    
    def create_insane_battle(self, user_id: str, battle_type: str = 'insane_lock') -> Dict[str, Any]:
        """Create insane battle"""
        if battle_type not in self.battle_types:
            return {'success': False, 'error': 'Invalid battle type'}
        
        battle_config = self.battle_types[battle_type]
        
        # Check energy
        from backend.services.ultra_resource_controller import ultra_resource_controller
        energy = ultra_resource_controller.get_energy_status(user_id)
        
        energy_data = energy.get('energy', {})
        for energy_type, cost in battle_config['energy_cost'].items():
            if energy_data.get(energy_type, 0) < cost:
                return {
                    'success': False,
                    'error': f'Insufficient {energy_type} energy. Need {cost}, have {energy_data.get(energy_type, 0)}'
                }
        
        # Create battle
        battle_id = str(uuid.uuid4())
        battle = {
            'battle_id': battle_id,
            'user_id': user_id,
            'battle_type': battle_type,
            'battle_name': battle_config['name'],
            'difficulty': battle_config['difficulty'],
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'energy_cost': battle_config['energy_cost'],
            'base_reward': float(battle_config['base_reward']),
            'opponent_power': random.randint(1000, 5000),
            'user_power': random.randint(500, 2000)
        }
        
        self.active_battles[battle_id] = battle
        
        return {
            'success': True,
            'battle': battle,
            'message': f'Created {battle_config["name"]} battle!'
        }
    
    def complete_battle(self, battle_id: str, victory: bool = False) -> Dict[str, Any]:
        """Complete battle"""
        if battle_id not in self.active_battles:
            return {'success': False, 'error': 'Battle not found'}
        
        battle = self.active_battles[battle_id]
        user_id = battle['user_id']
        
        # Calculate result
        if victory:
            reward = battle['base_reward']
            result = 'victory'
        else:
            reward = battle['base_reward'] * Decimal('0.1')
            result = 'defeat'
        
        # Record battle
        if user_id not in self.battle_history:
            self.battle_history[user_id] = []
        
        battle_result = {
            'battle_id': battle_id,
            'battle_type': battle['battle_type'],
            'result': result,
            'reward': float(reward),
            'completed_at': datetime.utcnow().isoformat()
        }
        
        self.battle_history[user_id].append(battle_result)
        
        # Remove from active
        del self.active_battles[battle_id]
        
        # Award cash
        from backend.services.monetization_cash_generator import monetization_cash_generator
        cash_result = monetization_cash_generator.generate_cash(
            user_id,
            'battle_victories',
            reward if victory else reward * Decimal('0.5')
        )
        
        return {
            'success': True,
            'battle_result': battle_result,
            'cash_awarded': cash_result,
            'message': f'Battle {result}! Reward: {float(reward)}'
        }
    
    def get_user_battles(self, user_id: str) -> Dict[str, Any]:
        """Get user battles"""
        active = [
            b for b in self.active_battles.values()
            if b['user_id'] == user_id
        ]
        
        history = self.battle_history.get(user_id, [])
        
        return {
            'success': True,
            'user_id': user_id,
            'active_battles': active,
            'battle_history': history[-10:],  # Last 10
            'total_battles': len(history),
            'victories': len([b for b in history if b['result'] == 'victory'])
        }

# Global instance
insane_battle_system = InsaneBattleSystem()

