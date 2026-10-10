"""
Group Destruction System - Destroy, merge, and takeover groups
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from collections import defaultdict


class DestructionAction:
    """Represents a destruction action"""
    
    def __init__(self, action_id: str, action_type: str, user_id: str, group_id: str, details: str = ''):
        self.id = action_id
        self.action_type = action_type  # destroy, merge, takeover, conquer
        self.user_id = user_id
        self.group_id = group_id
        self.details = details
        self.timestamp = datetime.utcnow()
        self.result = 'pending'  # pending, success, failed
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'action': self.action_type,
            'user_id': self.user_id,
            'group_id': self.group_id,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'result': self.result
        }


class GroupDestructionSystem:
    """Manages group destruction, merging, and takeover"""
    
    def __init__(self):
        self.destruction_history = []  # List of DestructionAction
        self.pending_takeovers = {}  # {takeover_id: takeover_data}
        self.territories = {}  # {territory_id: territory_data}
        self.group_territories = defaultdict(list)  # {group_id: [territory_ids]}
    
    def destroy_group(self, group_id: str, user_id: str, group_type: str = 'clan') -> Dict[str, Any]:
        """Destroy a group permanently"""
        action_id = str(uuid.uuid4())
        action = DestructionAction(action_id, 'destroy', user_id, group_id, f'Destroyed {group_type} {group_id}')
        action.result = 'success'
        self.destruction_history.append(action)
        
        return {
            'success': True,
            'action_id': action_id,
            'message': f'{group_type.capitalize()} destroyed',
            'action': action.to_dict()
        }
    
    def merge_groups(self, group1_id: str, group2_id: str, user_id: str, new_name: str = None) -> Dict[str, Any]:
        """Merge two groups into one"""
        action_id = str(uuid.uuid4())
        action = DestructionAction(action_id, 'merge', user_id, group1_id, f'Merged {group1_id} and {group2_id}')
        action.result = 'success'
        self.destruction_history.append(action)
        
        return {
            'success': True,
            'action_id': action_id,
            'merged_group_id': str(uuid.uuid4()),
            'message': 'Groups merged successfully',
            'action': action.to_dict()
        }
    
    def initiate_takeover(self, group_id: str, user_id: str, attacking_group_id: str) -> Dict[str, Any]:
        """Initiate a takeover of a group"""
        takeover_id = str(uuid.uuid4())
        self.pending_takeovers[takeover_id] = {
            'id': takeover_id,
            'target_group_id': group_id,
            'attacking_group_id': attacking_group_id,
            'user_id': user_id,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        action_id = str(uuid.uuid4())
        action = DestructionAction(action_id, 'takeover', user_id, group_id, f'Takeover initiated for {group_id}')
        action.result = 'pending'
        self.destruction_history.append(action)
        
        return {
            'success': True,
            'takeover_id': takeover_id,
            'message': 'Takeover initiated. Battle required to complete.',
            'action': action.to_dict()
        }
    
    def conquer_territory(self, territory_id: str, user_id: str, attacking_group_id: str) -> Dict[str, Any]:
        """Conquer a territory from another group"""
        action_id = str(uuid.uuid4())
        action = DestructionAction(action_id, 'conquer', user_id, territory_id, f'Conquered territory {territory_id}')
        action.result = 'pending'
        self.destruction_history.append(action)
        
        return {
            'success': True,
            'action_id': action_id,
            'message': 'Territory conquest initiated. Battle required to complete.',
            'action': action.to_dict()
        }
    
    def get_destruction_history(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get destruction history for a user"""
        user_actions = [a for a in self.destruction_history if a.user_id == user_id]
        user_actions.sort(key=lambda x: x.timestamp, reverse=True)
        return [a.to_dict() for a in user_actions[:limit]]
    
    def create_territory(self, territory_id: str, name: str, owner_group_id: str, value: int = 1000) -> Dict[str, Any]:
        """Create a new territory"""
        self.territories[territory_id] = {
            'id': territory_id,
            'name': name,
            'owner_group_id': owner_group_id,
            'value': value,
            'created_at': datetime.utcnow().isoformat()
        }
        self.group_territories[owner_group_id].append(territory_id)
        
        return {
            'success': True,
            'territory': self.territories[territory_id]
        }
    
    def get_available_territories(self, exclude_group_id: str = None) -> List[Dict]:
        """Get territories available for conquest"""
        territories = []
        for territory_id, territory in self.territories.items():
            if exclude_group_id and territory['owner_group_id'] == exclude_group_id:
                continue
            territories.append(territory)
        return territories


# Global instance
group_destruction_system = GroupDestructionSystem()

