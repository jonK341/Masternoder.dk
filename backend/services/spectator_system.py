"""
Spectator System
Allows users to watch battles in real-time
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

try:
    from backend.services.battle_system import battle_system
    from backend.services.quick_battle_system import quick_battle
except ImportError:
    battle_system = None
    quick_battle = None


class SpectatorSystem:
    """System for spectating battles"""
    
    def __init__(self):
        self.spectators = {}  # battle_id -> [spectator_data]
        self.user_spectating = {}  # user_id -> battle_id
        self.spectator_queue = {}  # battle_id -> [user_ids]
        self.max_spectators_per_battle = 50
    
    def join_spectator_queue(self, user_id: str, battle_id: str) -> Dict[str, Any]:
        """
        Join spectator queue for a battle
        
        Args:
            user_id: User wanting to spectate
            battle_id: Battle to spectate
            
        Returns:
            Queue join result
        """
        # Check if battle exists
        battle = None
        if battle_system and battle_id in battle_system.battles:
            battle = battle_system.battles[battle_id]
        elif quick_battle and battle_id in quick_battle.battles:
            battle = quick_battle.battles[battle_id]
        
        if not battle:
            return {
                'success': False,
                'error': 'Battle not found'
            }
        
        # Check if battle is active
        if battle.get('status') != 'active':
            return {
                'success': False,
                'error': 'Battle is not active'
            }
        
        # Check if already spectating
        if user_id in self.user_spectating:
            if self.user_spectating[user_id] == battle_id:
                return {
                    'success': True,
                    'status': 'already_spectating',
                    'battle_id': battle_id
                }
        
        # Check spectator limit
        current_spectators = len(self.spectators.get(battle_id, []))
        if current_spectators >= self.max_spectators_per_battle:
            # Add to queue
            if battle_id not in self.spectator_queue:
                self.spectator_queue[battle_id] = []
            if user_id not in self.spectator_queue[battle_id]:
                self.spectator_queue[battle_id].append(user_id)
            
            return {
                'success': True,
                'status': 'queued',
                'position': len(self.spectator_queue[battle_id]),
                'message': 'Added to spectator queue'
            }
        
        # Add as spectator
        spectator_data = {
            'user_id': user_id,
            'battle_id': battle_id,
            'joined_at': datetime.utcnow().isoformat(),
            'last_update': datetime.utcnow().isoformat()
        }
        
        if battle_id not in self.spectators:
            self.spectators[battle_id] = []
        self.spectators[battle_id].append(spectator_data)
        self.user_spectating[user_id] = battle_id
        
        return {
            'success': True,
            'status': 'spectating',
            'battle_id': battle_id,
            'spectator_count': len(self.spectators[battle_id])
        }
    
    def leave_spectator(self, user_id: str) -> Dict[str, Any]:
        """Leave spectator mode"""
        if user_id not in self.user_spectating:
            return {
                'success': False,
                'error': 'Not spectating any battle'
            }
        
        battle_id = self.user_spectating[user_id]
        
        # Remove from spectators
        if battle_id in self.spectators:
            self.spectators[battle_id] = [
                s for s in self.spectators[battle_id] 
                if s['user_id'] != user_id
            ]
        
        # Remove from queue
        if battle_id in self.spectator_queue:
            self.spectator_queue[battle_id] = [
                u for u in self.spectator_queue[battle_id] 
                if u != user_id
            ]
        
        del self.user_spectating[user_id]
        
        # Process queue if space available
        if battle_id in self.spectator_queue and self.spectator_queue[battle_id]:
            if len(self.spectators.get(battle_id, [])) < self.max_spectators_per_battle:
                next_user = self.spectator_queue[battle_id].pop(0)
                self.join_spectator_queue(next_user, battle_id)
        
        return {
            'success': True,
            'message': 'Left spectator mode'
        }
    
    def get_spectator_count(self, battle_id: str) -> int:
        """Get number of spectators for a battle"""
        return len(self.spectators.get(battle_id, []))
    
    def get_spectators(self, battle_id: str) -> List[Dict[str, Any]]:
        """Get list of spectators for a battle"""
        return self.spectators.get(battle_id, [])
    
    def update_spectator_activity(self, user_id: str):
        """Update spectator activity timestamp"""
        if user_id in self.user_spectating:
            battle_id = self.user_spectating[user_id]
            if battle_id in self.spectators:
                for spectator in self.spectators[battle_id]:
                    if spectator['user_id'] == user_id:
                        spectator['last_update'] = datetime.utcnow().isoformat()
                        break
    
    def cleanup_inactive_spectators(self, timeout_seconds: int = 300):
        """Remove inactive spectators (5 minutes timeout)"""
        current_time = datetime.utcnow()
        removed_count = 0
        
        for battle_id, spectators in list(self.spectators.items()):
            active_spectators = []
            for spectator in spectators:
                last_update = datetime.fromisoformat(spectator['last_update'])
                if (current_time - last_update).total_seconds() < timeout_seconds:
                    active_spectators.append(spectator)
                else:
                    # Remove inactive spectator
                    user_id = spectator['user_id']
                    if user_id in self.user_spectating:
                        del self.user_spectating[user_id]
                    removed_count += 1
            
            if active_spectators:
                self.spectators[battle_id] = active_spectators
            else:
                del self.spectators[battle_id]
        
        return removed_count
    
    def get_spectatable_battles(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get list of battles that can be spectated"""
        spectatable = []
        
        # Get active battles from battle system
        if battle_system:
            for battle_id, battle in battle_system.battles.items():
                if battle.get('status') == 'active':
                    spectator_count = self.get_spectator_count(battle_id)
                    spectatable.append({
                        'battle_id': battle_id,
                        'battle_type': battle.get('battle_type', 'standard'),
                        'spectator_count': spectator_count,
                        'max_spectators': self.max_spectators_per_battle,
                        'can_spectate': spectator_count < self.max_spectators_per_battle,
                        'created_at': battle.get('created_at')
                    })
        
        # Get active battles from quick battle system
        if quick_battle:
            for battle_id, battle in quick_battle.battles.items():
                if battle.get('status') == 'active' and battle_id not in [b['battle_id'] for b in spectatable]:
                    spectator_count = self.get_spectator_count(battle_id)
                    spectatable.append({
                        'battle_id': battle_id,
                        'battle_type': 'quick',
                        'spectator_count': spectator_count,
                        'max_spectators': self.max_spectators_per_battle,
                        'can_spectate': spectator_count < self.max_spectators_per_battle,
                        'created_at': battle.get('created_at')
                    })
        
        # Sort by spectator count (most watched first)
        spectatable.sort(key=lambda x: x['spectator_count'], reverse=True)
        
        return spectatable[:limit]


# Global instance
spectator_system = SpectatorSystem()
