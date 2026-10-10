"""
Battle Techno Tunnel Magi - Territory Expansion System
Expands battlefield to new territories through techno tunnel magic
Integrated with Intelligence and Quick Battle
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random
import math

class BattleTechnoTunnelMagi:
    """Battle Techno Tunnel Magic System for Territory Expansion"""
    
    def __init__(self):
        self.territories = self._initialize_territories()
        self.active_tunnels = defaultdict(dict)  # {user_id: {tunnel_id: tunnel_data}}
        self.territory_expansions = defaultdict(list)  # {user_id: [expansion_data]}
        self.magic_resources = defaultdict(dict)  # {user_id: magic_resources}
        self.intelligence_connections = defaultdict(dict)  # {user_id: intelligence_data}
    
    def _initialize_territories(self) -> Dict[str, Dict[str, Any]]:
        """Initialize available territories"""
        return {
            'techno_core': {
                'id': 'techno_core',
                'name': 'Techno Core',
                'description': 'The central techno realm, source of all tunnel magic',
                'power_level': 1000,
                'magic_affinity': 'techno',
                'unlocked': True,
                'expansion_cost': 0
            },
            'digital_wasteland': {
                'id': 'digital_wasteland',
                'name': 'Digital Wasteland',
                'description': 'A desolate digital realm filled with corrupted data',
                'power_level': 1500,
                'magic_affinity': 'techno',
                'unlocked': False,
                'expansion_cost': 500
            },
            'cyber_nexus': {
                'id': 'cyber_nexus',
                'name': 'Cyber Nexus',
                'description': 'A network hub connecting multiple dimensions',
                'power_level': 2000,
                'magic_affinity': 'techno',
                'unlocked': False,
                'expansion_cost': 1000
            },
            'quantum_void': {
                'id': 'quantum_void',
                'name': 'Quantum Void',
                'description': 'A realm where quantum mechanics and magic collide',
                'power_level': 2500,
                'magic_affinity': 'quantum',
                'unlocked': False,
                'expansion_cost': 2000
            },
            'neural_network': {
                'id': 'neural_network',
                'name': 'Neural Network',
                'description': 'A living network of interconnected intelligence nodes',
                'power_level': 3000,
                'magic_affinity': 'neural',
                'unlocked': False,
                'expansion_cost': 3000
            },
            'data_stream': {
                'id': 'data_stream',
                'name': 'Data Stream',
                'description': 'A flowing river of pure information and energy',
                'power_level': 3500,
                'magic_affinity': 'data',
                'unlocked': False,
                'expansion_cost': 4000
            },
            'virtual_reality': {
                'id': 'virtual_reality',
                'name': 'Virtual Reality',
                'description': 'A simulated realm where anything is possible',
                'power_level': 4000,
                'magic_affinity': 'virtual',
                'unlocked': False,
                'expansion_cost': 5000
            },
            'ai_dimension': {
                'id': 'ai_dimension',
                'name': 'AI Dimension',
                'description': 'A realm controlled by artificial intelligence entities',
                'power_level': 5000,
                'magic_affinity': 'ai',
                'unlocked': False,
                'expansion_cost': 7500
            }
        }
    
    def create_techno_tunnel(
        self,
        user_id: str,
        source_territory: str,
        target_territory: str,
        intelligence_level: int = 50
    ) -> Dict[str, Any]:
        """Create a techno tunnel to expand to new territory"""
        tunnel_id = f"tunnel_{user_id}_{datetime.utcnow().timestamp()}"
        
        # Check if source territory is unlocked
        if source_territory not in self.territories:
            return {'success': False, 'error': 'Source territory not found'}
        
        source = self.territories[source_territory]
        if not source.get('unlocked'):
            return {'success': False, 'error': 'Source territory not unlocked'}
        
        # Check if target territory exists
        if target_territory not in self.territories:
            return {'success': False, 'error': 'Target territory not found'}
        
        target = self.territories[target_territory]
        
        # Check if already unlocked
        if target.get('unlocked'):
            return {'success': False, 'error': 'Target territory already unlocked'}
        
        # Calculate tunnel cost based on intelligence
        base_cost = target['expansion_cost']
        intelligence_discount = intelligence_level * 0.01  # 1% discount per intelligence point
        final_cost = max(100, base_cost * (1 - intelligence_discount))
        
        # Check if user has enough resources
        user_resources = self.magic_resources.get(user_id, {'techno_energy': 0})
        if user_resources.get('techno_energy', 0) < final_cost:
            return {
                'success': False,
                'error': 'Insufficient techno energy',
                'required': final_cost,
                'available': user_resources.get('techno_energy', 0)
            }
        
        # Create tunnel
        tunnel = {
            'tunnel_id': tunnel_id,
            'user_id': user_id,
            'source_territory': source_territory,
            'target_territory': target_territory,
            'intelligence_level': intelligence_level,
            'cost': final_cost,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'completion_time': (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
        
        # Deduct resources
        user_resources['techno_energy'] -= final_cost
        self.magic_resources[user_id] = user_resources
        
        # Store tunnel
        self.active_tunnels[user_id][tunnel_id] = tunnel
        
        # Unlock territory after tunnel completion
        self.territories[target_territory]['unlocked'] = True
        
        # Record expansion
        expansion = {
            'expansion_id': f"expansion_{datetime.utcnow().timestamp()}",
            'user_id': user_id,
            'territory_id': target_territory,
            'territory_name': target['name'],
            'tunnel_id': tunnel_id,
            'cost': final_cost,
            'intelligence_used': intelligence_level,
            'expanded_at': datetime.utcnow().isoformat()
        }
        self.territory_expansions[user_id].append(expansion)
        
        return {
            'success': True,
            'tunnel': tunnel,
            'expansion': expansion,
            'territory': target
        }
    
    def get_available_territories(self, user_id: str) -> Dict[str, Any]:
        """Get available territories for expansion"""
        unlocked = []
        locked = []
        
        for territory_id, territory in self.territories.items():
            if territory.get('unlocked'):
                unlocked.append(territory)
            else:
                locked.append(territory)
        
        return {
            'success': True,
            'unlocked_territories': unlocked,
            'locked_territories': locked,
            'total_territories': len(self.territories),
            'unlocked_count': len(unlocked),
            'locked_count': len(locked)
        }
    
    def get_user_expansions(self, user_id: str) -> Dict[str, Any]:
        """Get user's territory expansions"""
        expansions = self.territory_expansions.get(user_id, [])
        active_tunnels = list(self.active_tunnels.get(user_id, {}).values())
        
        return {
            'success': True,
            'expansions': expansions,
            'active_tunnels': active_tunnels,
            'total_expansions': len(expansions),
            'active_tunnel_count': len(active_tunnels)
        }
    
    def get_techno_magic_resources(self, user_id: str) -> Dict[str, Any]:
        """Get user's techno magic resources"""
        resources = self.magic_resources.get(user_id, {
            'techno_energy': 0,
            'magic_crystals': 0,
            'intelligence_points': 0
        })
        
        return {
            'success': True,
            'resources': resources
        }
    
    def add_techno_energy(self, user_id: str, amount: int) -> Dict[str, Any]:
        """Add techno energy to user"""
        if user_id not in self.magic_resources:
            self.magic_resources[user_id] = {
                'techno_energy': 0,
                'magic_crystals': 0,
                'intelligence_points': 0
            }
        
        self.magic_resources[user_id]['techno_energy'] += amount
        
        return {
            'success': True,
            'new_balance': self.magic_resources[user_id]['techno_energy']
        }
    
    def integrate_with_intelligence(
        self,
        user_id: str,
        intelligence_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Integrate techno tunnel magic with intelligence system"""
        intelligence_level = intelligence_data.get('intelligence_level', 50)
        intelligence_bonus = intelligence_level * 0.02  # 2% bonus per intelligence point
        
        # Update intelligence connections
        self.intelligence_connections[user_id] = {
            'intelligence_level': intelligence_level,
            'intelligence_bonus': intelligence_bonus,
            'integrated_at': datetime.utcnow().isoformat(),
            'bonus_applied': True
        }
        
        # Apply bonus to resources
        if user_id not in self.magic_resources:
            self.magic_resources[user_id] = {
                'techno_energy': 0,
                'magic_crystals': 0,
                'intelligence_points': intelligence_level
            }
        else:
            self.magic_resources[user_id]['intelligence_points'] = intelligence_level
        
        return {
            'success': True,
            'intelligence_level': intelligence_level,
            'intelligence_bonus': intelligence_bonus,
            'integration': self.intelligence_connections[user_id]
        }
    
    def quick_battle_expansion(
        self,
        user_id: str,
        battle_id: str,
        intelligence_level: int = 50
    ) -> Dict[str, Any]:
        """Quick battle territory expansion"""
        # Get available locked territories
        available = [t for t in self.territories.values() if not t.get('unlocked')]
        
        if not available:
            return {'success': False, 'error': 'No territories available for expansion'}
        
        # Select random territory
        target = random.choice(available)
        
        # Use Techno Core as source (always unlocked)
        result = self.create_techno_tunnel(
            user_id=user_id,
            source_territory='techno_core',
            target_territory=target['id'],
            intelligence_level=intelligence_level
        )
        
        if result.get('success'):
            return {
                'success': True,
                'battle_id': battle_id,
                'expansion': result['expansion'],
                'territory': result['territory'],
                'message': f"Battlefield expanded to {target['name']}!"
            }
        
        return result


# Global instance
battle_techno_tunnel_magi = BattleTechnoTunnelMagi()

