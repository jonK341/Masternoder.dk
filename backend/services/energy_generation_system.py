"""
Energy Generation System
21 new agent abilities with synergy and energy production
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json

logger = logging.getLogger(__name__)

class EnergyGenerationSystem:
    """Manages energy generation from agent synergy and user actions"""
    
    def __init__(self):
        # 21 New Agent Abilities
        self.agent_abilities = {
            'power_boost': {'name': 'Power Boost', 'energy_gen': 10, 'synergy_bonus': 0.1},
            'energy_flow': {'name': 'Energy Flow', 'energy_gen': 15, 'synergy_bonus': 0.15},
            'synergy_link': {'name': 'Synergy Link', 'energy_gen': 12, 'synergy_bonus': 0.2},
            'collective_power': {'name': 'Collective Power', 'energy_gen': 20, 'synergy_bonus': 0.25},
            'energy_fusion': {'name': 'Energy Fusion', 'energy_gen': 18, 'synergy_bonus': 0.3},
            'power_amplifier': {'name': 'Power Amplifier', 'energy_gen': 14, 'synergy_bonus': 0.18},
            'energy_conduit': {'name': 'Energy Conduit', 'energy_gen': 16, 'synergy_bonus': 0.22},
            'synergy_network': {'name': 'Synergy Network', 'energy_gen': 22, 'synergy_bonus': 0.28},
            'power_resonance': {'name': 'Power Resonance', 'energy_gen': 13, 'synergy_bonus': 0.16},
            'energy_cascade': {'name': 'Energy Cascade', 'energy_gen': 19, 'synergy_bonus': 0.24},
            'collective_boost': {'name': 'Collective Boost', 'energy_gen': 17, 'synergy_bonus': 0.21},
            'synergy_amplification': {'name': 'Synergy Amplification', 'energy_gen': 21, 'synergy_bonus': 0.27},
            'energy_synthesis': {'name': 'Energy Synthesis', 'energy_gen': 15, 'synergy_bonus': 0.19},
            'power_network': {'name': 'Power Network', 'energy_gen': 23, 'synergy_bonus': 0.29},
            'energy_harmony': {'name': 'Energy Harmony', 'energy_gen': 11, 'synergy_bonus': 0.14},
            'synergy_fusion': {'name': 'Synergy Fusion', 'energy_gen': 20, 'synergy_bonus': 0.26},
            'collective_resonance': {'name': 'Collective Resonance', 'energy_gen': 18, 'synergy_bonus': 0.23},
            'energy_matrix': {'name': 'Energy Matrix', 'energy_gen': 24, 'synergy_bonus': 0.31},
            'power_convergence': {'name': 'Power Convergence', 'energy_gen': 16, 'synergy_bonus': 0.2},
            'synergy_cascade': {'name': 'Synergy Cascade', 'energy_gen': 19, 'synergy_bonus': 0.25},
            'ultimate_synergy': {'name': 'Ultimate Synergy', 'energy_gen': 25, 'synergy_bonus': 0.35}
        }
        
        # Energy Types
        self.energy_types = {
            'active': {'name': 'Active Energy', 'source': 'user_actions', 'base_gen': 5},
            'synergy': {'name': 'Synergy Energy', 'source': 'agent_combinations', 'base_gen': 10},
            'system': {'name': 'System Energy', 'source': 'system_operations', 'base_gen': 3},
            'creative': {'name': 'Creative Energy', 'source': 'content_creation', 'base_gen': 8}
        }
        
        self.user_energy = {}  # user_id -> energy_data
        self.agent_combinations = {}  # combination_id -> synergy_data
        self.machine_energy = {}  # machine_id -> energy_data
    
    def generate_energy(self, user_id: str, energy_type: str, amount: float = None, 
                       metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Generate energy for a user"""
        metadata = metadata or {}
        
        if energy_type not in self.energy_types:
            return {'success': False, 'error': 'Invalid energy type'}
        
        energy_config = self.energy_types[energy_type]
        base_amount = amount or energy_config['base_gen']
        
        # Apply multipliers
        multiplier = 1.0
        
        # Agent synergy bonus
        active_agents = metadata.get('active_agents', [])
        if active_agents:
            synergy_bonus = self._calculate_synergy_bonus(active_agents)
            multiplier += synergy_bonus
        
        # Machine/robot bonus
        machines_active = metadata.get('machines_active', 0)
        if machines_active > 0:
            machine_bonus = machines_active * 0.1  # 10% per machine
            multiplier += machine_bonus
        
        # Activity bonus
        activity_bonus = metadata.get('activity_bonus', 0)
        multiplier += activity_bonus
        
        total_energy = int(base_amount * multiplier)
        
        # Update user energy
        if user_id not in self.user_energy:
            self.user_energy[user_id] = {
                'total_energy': 0,
                'energy_by_type': {},
                'generation_history': []
            }
        
        user_energy_data = self.user_energy[user_id]
        user_energy_data['total_energy'] += total_energy
        user_energy_data['energy_by_type'][energy_type] = \
            user_energy_data['energy_by_type'].get(energy_type, 0) + total_energy
        
        user_energy_data['generation_history'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'energy_type': energy_type,
            'amount': total_energy,
            'base_amount': base_amount,
            'multiplier': multiplier,
            'metadata': metadata
        })
        
        return {
            'success': True,
            'user_id': user_id,
            'energy_type': energy_type,
            'base_amount': base_amount,
            'multiplier': multiplier,
            'total_energy': total_energy,
            'user_total_energy': user_energy_data['total_energy']
        }
    
    def _calculate_synergy_bonus(self, agent_ids: List[str]) -> float:
        """Calculate synergy bonus from agent combinations"""
        if len(agent_ids) < 2:
            return 0.0
        
        total_bonus = 0.0
        
        # Check for ability combinations
        for agent_id in agent_ids:
            # Assume agents have abilities (simplified)
            ability_count = len(agent_ids) - 1  # Synergy with other agents
            total_bonus += ability_count * 0.05  # 5% per agent synergy
        
        # Check for specific ability synergies
        if len(agent_ids) >= 3:
            total_bonus += 0.1  # Triple synergy bonus
        if len(agent_ids) >= 5:
            total_bonus += 0.2  # Quintuple synergy bonus
        
        return min(total_bonus, 1.0)  # Cap at 100% bonus
    
    def activate_agent_ability(self, user_id: str, ability_id: str, 
                              agent_ids: List[str] = None) -> Dict[str, Any]:
        """Activate an agent ability for energy generation"""
        if ability_id not in self.agent_abilities:
            return {'success': False, 'error': 'Ability not found'}
        
        ability = self.agent_abilities[ability_id]
        agent_ids = agent_ids or []
        
        # Generate synergy energy
        base_energy = ability['energy_gen']
        synergy_multiplier = 1.0 + (len(agent_ids) * ability['synergy_bonus'])
        
        total_energy = int(base_energy * synergy_multiplier)
        
        # Generate energy
        result = self.generate_energy(
            user_id,
            'synergy',
            total_energy,
            {
                'ability_id': ability_id,
                'ability_name': ability['name'],
                'active_agents': agent_ids,
                'synergy_multiplier': synergy_multiplier
            }
        )
        
        return {
            'success': True,
            'ability_id': ability_id,
            'ability_name': ability['name'],
            'energy_generated': total_energy,
            'synergy_multiplier': synergy_multiplier,
            'result': result
        }
    
    def create_machine_energy(self, machine_id: str, energy_output: float) -> Dict[str, Any]:
        """Create energy from machine/robot"""
        if machine_id not in self.machine_energy:
            self.machine_energy[machine_id] = {
                'total_generated': 0,
                'output_history': []
            }
        
        machine_data = self.machine_energy[machine_id]
        machine_data['total_generated'] += energy_output
        machine_data['output_history'].append({
            'timestamp': datetime.utcnow().isoformat(),
            'output': energy_output
        })
        
        return {
            'success': True,
            'machine_id': machine_id,
            'energy_output': energy_output,
            'total_generated': machine_data['total_generated']
        }
    
    def get_user_energy(self, user_id: str) -> Dict[str, Any]:
        """Get user energy statistics"""
        energy_data = self.user_energy.get(user_id, {
            'total_energy': 0,
            'energy_by_type': {},
            'generation_history': []
        })
        
        return {
            'user_id': user_id,
            'total_energy': energy_data['total_energy'],
            'energy_by_type': energy_data['energy_by_type'],
            'recent_generation': energy_data['generation_history'][-10:] if energy_data['generation_history'] else []
        }
    
    def get_available_abilities(self) -> Dict[str, Any]:
        """Get all available agent abilities"""
        return {
            'total_abilities': len(self.agent_abilities),
            'abilities': self.agent_abilities
        }

energy_generation_system = EnergyGenerationSystem()
