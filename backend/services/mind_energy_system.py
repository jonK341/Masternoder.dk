"""
Mind Energy System - HP/Mana style energy for generators
Like hit points and mana points for video generation
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import json
import os

class MindEnergySystem:
    """
    Mind Energy System - Generator Energy (HP/Mana style)
    Enhanced with multiple generator types, upgrades, and efficiency tracking
    """
    
    def __init__(self):
        self.data_dir = 'data/mind_energy'
        os.makedirs(self.data_dir, exist_ok=True)
        self.max_energy = 100
        self.regeneration_rate = 1.0  # Energy per minute
        self.generator_cost = 20  # Cost per video generation
        
        # Generator types configuration
        self.generator_types = {
            'basic': {
                'name': 'Basic Generator',
                'base_max_energy': 100,
                'base_regeneration': 1.0,
                'base_efficiency': 1.0,
                'upgrade_cost_multiplier': 1.0
            },
            'advanced': {
                'name': 'Advanced Generator',
                'base_max_energy': 200,
                'base_regeneration': 2.0,
                'base_efficiency': 1.5,
                'upgrade_cost_multiplier': 2.0
            },
            'quantum': {
                'name': 'Quantum Generator',
                'base_max_energy': 500,
                'base_regeneration': 5.0,
                'base_efficiency': 2.5,
                'upgrade_cost_multiplier': 5.0
            },
            'plasma': {
                'name': 'Plasma Generator',
                'base_max_energy': 1000,
                'base_regeneration': 10.0,
                'base_efficiency': 5.0,
                'upgrade_cost_multiplier': 10.0
            }
        }
    
    def get_energy(self, user_id: str) -> Dict[str, Any]:
        """Get current mind energy for user (enhanced with multiple generators)"""
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        
        if os.path.exists(energy_file):
            with open(energy_file, 'r') as f:
                data = json.load(f)
        else:
            data = {
                'generators': {
                    'basic': {
                        'level': 1,
                        'max_energy': 100,
                        'current_energy': 100,
                        'regeneration_rate': 1.0,
                        'efficiency': 1.0,
                        'total_energy_generated': 0,
                        'total_energy_used': 0,
                        'upgrade_count': 0
                    }
                },
                'active_generator': 'basic',
                'last_update': datetime.utcnow().isoformat(),
                'total_energy_used': 0,
                'total_energy_regenerated': 0
            }
        
        # Ensure generators structure exists
        if 'generators' not in data:
            data['generators'] = {
                'basic': {
                    'level': 1,
                    'max_energy': 100,
                    'current_energy': data.get('generator_energy', 100),
                    'regeneration_rate': 1.0,
                    'efficiency': 1.0,
                    'total_energy_generated': 0,
                    'total_energy_used': 0,
                    'upgrade_count': 0
                }
            }
            data['active_generator'] = 'basic'
        
        # Regenerate energy for all generators based on time passed
        last_update = datetime.fromisoformat(data.get('last_update', datetime.utcnow().isoformat()))
        time_passed = (datetime.utcnow() - last_update).total_seconds() / 60  # minutes
        
        generators_data = {}
        total_energy = 0
        total_max_energy = 0
        
        for gen_type, gen_config in self.generator_types.items():
            if gen_type not in data['generators']:
                continue
                
            gen_data = data['generators'][gen_type]
            base_config = gen_config
            
            # Calculate current stats based on level
            level = gen_data.get('level', 1)
            max_energy = base_config['base_max_energy'] * (1 + (level - 1) * 0.2)
            regen_rate = base_config['base_regeneration'] * (1 + (level - 1) * 0.15)
            efficiency = base_config['base_efficiency'] * (1 + (level - 1) * 0.1)
            
            # Regenerate energy
            current_energy = gen_data.get('current_energy', max_energy)
            energy_regenerated = time_passed * regen_rate * efficiency
            current_energy = min(max_energy, current_energy + energy_regenerated)
            
            # Update generator data
            gen_data['current_energy'] = current_energy
            gen_data['max_energy'] = max_energy
            gen_data['regeneration_rate'] = regen_rate
            gen_data['efficiency'] = efficiency
            gen_data['total_energy_regenerated'] = gen_data.get('total_energy_regenerated', 0) + energy_regenerated
            
            generators_data[gen_type] = {
                'name': base_config['name'],
                'level': level,
                'current_energy': current_energy,
                'max_energy': max_energy,
                'regeneration_rate': regen_rate,
                'efficiency': efficiency,
                'energy_percentage': (current_energy / max_energy) * 100,
                'time_to_full': ((max_energy - current_energy) / (regen_rate * efficiency)) if current_energy < max_energy else 0,
                'total_energy_generated': gen_data.get('total_energy_generated', 0),
                'total_energy_used': gen_data.get('total_energy_used', 0),
                'upgrade_count': gen_data.get('upgrade_count', 0)
            }
            
            total_energy += current_energy
            total_max_energy += max_energy
        
        # Update data
        data['generators'] = {k: v for k, v in data['generators'].items()}
        data['last_update'] = datetime.utcnow().isoformat()
        data['total_energy_regenerated'] = data.get('total_energy_regenerated', 0) + (time_passed * sum(g.get('regeneration_rate', 0) * g.get('efficiency', 1) for g in generators_data.values()))
        
        # Save
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        active_gen = data.get('active_generator', 'basic')
        active_gen_data = generators_data.get(active_gen, list(generators_data.values())[0] if generators_data else {})
        
        return {
            'generator_energy': active_gen_data.get('current_energy', 0),
            'max_energy': active_gen_data.get('max_energy', 100),
            'energy_percentage': active_gen_data.get('energy_percentage', 0),
            'regeneration_rate': active_gen_data.get('regeneration_rate', 1.0),
            'can_generate': active_gen_data.get('current_energy', 0) >= self.generator_cost,
            'time_to_full': active_gen_data.get('time_to_full', 0),
            'generators': generators_data,
            'active_generator': active_gen,
            'total_energy': total_energy,
            'total_max_energy': total_max_energy
        }
    
    def use_generator_energy(self, user_id: str, amount: int = None) -> Dict[str, Any]:
        """Use energy for generator"""
        if amount is None:
            amount = self.generator_cost
        
        energy_data = self.get_energy(user_id)
        current_energy = energy_data['generator_energy']
        
        if current_energy < amount:
            return {
                'success': False,
                'error': 'Insufficient energy',
                'current_energy': current_energy,
                'required': amount
            }
        
        # Deduct energy
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        with open(energy_file, 'r') as f:
            data = json.load(f)
        
        data['generator_energy'] = current_energy - amount
        data['total_energy_used'] = data.get('total_energy_used', 0) + amount
        data['last_update'] = datetime.utcnow().isoformat()
        
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'energy_used': amount,
            'remaining_energy': data['generator_energy'],
            'energy_percentage': (data['generator_energy'] / self.max_energy) * 100
        }
    
    def boost_energy(self, user_id: str, amount: int) -> Dict[str, Any]:
        """Boost energy (purchasable)"""
        energy_data = self.get_energy(user_id)
        current_energy = energy_data['generator_energy']
        
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        with open(energy_file, 'r') as f:
            data = json.load(f)
        
        new_energy = min(self.max_energy, current_energy + amount)
        data['generator_energy'] = new_energy
        data['total_energy_boosted'] = data.get('total_energy_boosted', 0) + amount
        data['last_update'] = datetime.utcnow().isoformat()
        
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'energy_boosted': amount,
            'current_energy': new_energy,
            'energy_percentage': (new_energy / self.max_energy) * 100
        }
    
    def upgrade_max_energy(self, user_id: str, new_max: int) -> Dict[str, Any]:
        """Upgrade max energy capacity (legacy support)"""
        energy_data = self.get_energy(user_id)
        
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        with open(energy_file, 'r') as f:
            data = json.load(f)
        
        # Upgrade active generator
        active_gen = data.get('active_generator', 'basic')
        if active_gen in data.get('generators', {}):
            gen_data = data['generators'][active_gen]
            gen_data['max_energy'] = new_max
            gen_data['current_energy'] = min(gen_data.get('current_energy', new_max), new_max)
            gen_data['level'] = gen_data.get('level', 1) + 1
            gen_data['upgrade_count'] = gen_data.get('upgrade_count', 0) + 1
        
        data['last_update'] = datetime.utcnow().isoformat()
        
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'new_max_energy': new_max,
            'current_energy': data['generators'][active_gen]['current_energy']
        }
    
    def upgrade_generator(self, user_id: str, generator_type: str) -> Dict[str, Any]:
        """Upgrade a specific generator"""
        if generator_type not in self.generator_types:
            return {'success': False, 'error': f'Invalid generator type: {generator_type}'}
        
        energy_data = self.get_energy(user_id)
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        
        with open(energy_file, 'r') as f:
            data = json.load(f)
        
        # Initialize generator if it doesn't exist
        if generator_type not in data.get('generators', {}):
            base_config = self.generator_types[generator_type]
            data['generators'][generator_type] = {
                'level': 1,
                'max_energy': base_config['base_max_energy'],
                'current_energy': base_config['base_max_energy'],
                'regeneration_rate': base_config['base_regeneration'],
                'efficiency': base_config['base_efficiency'],
                'total_energy_generated': 0,
                'total_energy_used': 0,
                'upgrade_count': 0
            }
        
        gen_data = data['generators'][generator_type]
        current_level = gen_data.get('level', 1)
        new_level = current_level + 1
        
        # Calculate new stats
        base_config = self.generator_types[generator_type]
        new_max_energy = base_config['base_max_energy'] * (1 + (new_level - 1) * 0.2)
        new_regen_rate = base_config['base_regeneration'] * (1 + (new_level - 1) * 0.15)
        new_efficiency = base_config['base_efficiency'] * (1 + (new_level - 1) * 0.1)
        
        # Update generator
        gen_data['level'] = new_level
        gen_data['max_energy'] = new_max_energy
        gen_data['current_energy'] = min(gen_data.get('current_energy', new_max_energy), new_max_energy)
        gen_data['regeneration_rate'] = new_regen_rate
        gen_data['efficiency'] = new_efficiency
        gen_data['upgrade_count'] = gen_data.get('upgrade_count', 0) + 1
        
        data['last_update'] = datetime.utcnow().isoformat()
        
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'generator_type': generator_type,
            'new_level': new_level,
            'new_max_energy': new_max_energy,
            'new_regeneration_rate': new_regen_rate,
            'new_efficiency': new_efficiency
        }
    
    def unlock_generator(self, user_id: str, generator_type: str) -> Dict[str, Any]:
        """Unlock a new generator type"""
        if generator_type not in self.generator_types:
            return {'success': False, 'error': f'Invalid generator type: {generator_type}'}
        
        energy_data = self.get_energy(user_id)
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        
        with open(energy_file, 'r') as f:
            data = json.load(f)
        
        # Check if already unlocked
        if generator_type in data.get('generators', {}):
            return {'success': False, 'error': 'Generator already unlocked'}
        
        # Unlock generator
        base_config = self.generator_types[generator_type]
        if 'generators' not in data:
            data['generators'] = {}
        
        data['generators'][generator_type] = {
            'level': 1,
            'max_energy': base_config['base_max_energy'],
            'current_energy': base_config['base_max_energy'],
            'regeneration_rate': base_config['base_regeneration'],
            'efficiency': base_config['base_efficiency'],
            'total_energy_generated': 0,
            'total_energy_used': 0,
            'upgrade_count': 0
        }
        
        data['last_update'] = datetime.utcnow().isoformat()
        
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'generator_type': generator_type,
            'generator_name': base_config['name']
        }
    
    def set_active_generator(self, user_id: str, generator_type: str) -> Dict[str, Any]:
        """Set the active generator"""
        energy_data = self.get_energy(user_id)
        
        if generator_type not in energy_data.get('generators', {}):
            return {'success': False, 'error': 'Generator not unlocked'}
        
        energy_file = os.path.join(self.data_dir, f'{user_id}.json')
        with open(energy_file, 'r') as f:
            data = json.load(f)
        
        data['active_generator'] = generator_type
        data['last_update'] = datetime.utcnow().isoformat()
        
        with open(energy_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        return {
            'success': True,
            'active_generator': generator_type
        }


# Global instance
mind_energy_system = MindEnergySystem()

