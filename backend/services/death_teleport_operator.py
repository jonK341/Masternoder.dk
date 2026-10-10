"""
DeathTeleport Operator - Similar to Timepocket
Quest Mission Operators System
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import random

class DeathTeleportOperator:
    """DeathTeleport Operator for Quest Missions"""
    
    def __init__(self):
        self.active_teleports = defaultdict(dict)  # {user_id: {teleport_id: teleport_data}}
        self.teleport_history = defaultdict(list)  # {user_id: [history_data]}
        self.quest_mission_operators = defaultdict(list)  # {user_id: [operator_data]}
        self.operator_types = {
            'death_teleport': {
                'name': 'DeathTeleport',
                'description': 'Instant teleportation with death consequences',
                'cooldown_minutes': 60,
                'cost': 100
            },
            'timepocket': {
                'name': 'Timepocket',
                'description': 'Time manipulation operator',
                'cooldown_minutes': 30,
                'cost': 50
            },
            'quantum_jump': {
                'name': 'Quantum Jump',
                'description': 'Quantum space-time jump',
                'cooldown_minutes': 45,
                'cost': 75
            }
        }
    
    def create_death_teleport(
        self,
        user_id: str,
        destination: str,
        quest_mission_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create DeathTeleport operator"""
        teleport_id = f"death_teleport_{datetime.utcnow().timestamp()}"
        
        # Check cooldown
        last_teleport = self._get_last_teleport(user_id, 'death_teleport')
        if last_teleport:
            last_time = datetime.fromisoformat(last_teleport['created_at'])
            cooldown = timedelta(minutes=self.operator_types['death_teleport']['cooldown_minutes'])
            if datetime.utcnow() - last_time < cooldown:
                remaining = cooldown - (datetime.utcnow() - last_time)
                return {
                    'success': False,
                    'error': f'Cooldown active. Wait {remaining.seconds // 60} minutes'
                }
        
        teleport = {
            'teleport_id': teleport_id,
            'user_id': user_id,
            'operator_type': 'death_teleport',
            'destination': destination,
            'quest_mission_id': quest_mission_id,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(minutes=5)).isoformat(),
            'death_consequences': True
        }
        
        self.active_teleports[user_id][teleport_id] = teleport
        
        # Record as quest mission operator
        operator_data = {
            'operator_id': teleport_id,
            'operator_type': 'death_teleport',
            'user_id': user_id,
            'quest_mission_id': quest_mission_id,
            'activated_at': datetime.utcnow().isoformat(),
            'status': 'active'
        }
        self.quest_mission_operators[user_id].append(operator_data)
        
        return {
            'success': True,
            'teleport': teleport,
            'operator': operator_data
        }
    
    def use_death_teleport(self, user_id: str, teleport_id: str) -> Dict[str, Any]:
        """Use DeathTeleport"""
        if user_id not in self.active_teleports or teleport_id not in self.active_teleports[user_id]:
            return {'success': False, 'error': 'Teleport not found'}
        
        teleport = self.active_teleports[user_id][teleport_id]
        
        if teleport['status'] != 'active':
            return {'success': False, 'error': 'Teleport not active'}
        
        # Check expiration
        expires_at = datetime.fromisoformat(teleport['expires_at'])
        if datetime.utcnow() > expires_at:
            teleport['status'] = 'expired'
            return {'success': False, 'error': 'Teleport expired'}
        
        # Use teleport
        teleport['status'] = 'used'
        teleport['used_at'] = datetime.utcnow().isoformat()
        
        # Record in history
        self.teleport_history[user_id].append({
            **teleport,
            'completed_at': datetime.utcnow().isoformat()
        })
        
        # Remove from active
        del self.active_teleports[user_id][teleport_id]
        
        return {
            'success': True,
            'teleport': teleport,
            'message': f"DeathTeleport to {teleport['destination']} completed"
        }
    
    def get_quest_mission_operators(self, user_id: str) -> Dict[str, Any]:
        """Get quest mission operators for user"""
        operators = self.quest_mission_operators.get(user_id, [])
        active_teleports = list(self.active_teleports.get(user_id, {}).values())
        
        return {
            'success': True,
            'operators': operators,
            'active_teleports': active_teleports,
            'operator_types': self.operator_types
        }
    
    def _get_last_teleport(self, user_id: str, operator_type: str) -> Optional[Dict[str, Any]]:
        """Get last teleport of type"""
        history = self.teleport_history.get(user_id, [])
        filtered = [t for t in history if t.get('operator_type') == operator_type]
        if filtered:
            return max(filtered, key=lambda x: x.get('created_at', ''))
        return None


# Global instance
death_teleport_operator = DeathTeleportOperator()

