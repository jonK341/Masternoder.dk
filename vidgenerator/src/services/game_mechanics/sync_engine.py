"""
Game Mechanics Sync Engine
Handles synchronization between client and server, peer downloads, and game state
"""
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import hashlib
import uuid

class SyncEngine:
    """Sync engine for game mechanics"""
    
    def __init__(self):
        self.sync_states = {}  # user_id -> sync_state
        self.peer_connections = {}  # user_id -> [peer_ids]
        self.download_peers = {}  # resource_id -> [peer_info]
    
    def create_sync_state(self, user_id: str, game_state: Dict) -> Dict:
        """Create sync state for user"""
        sync_id = str(uuid.uuid4())
        sync_state = {
            'sync_id': sync_id,
            'user_id': user_id,
            'game_state': game_state,
            'last_sync': datetime.now().isoformat(),
            'version': 1,
            'checksum': self._calculate_checksum(game_state)
        }
        self.sync_states[user_id] = sync_state
        return sync_state
    
    def sync_game_state(self, user_id: str, client_state: Dict, server_state: Dict) -> Dict:
        """Sync game state between client and server"""
        if user_id not in self.sync_states:
            return self.create_sync_state(user_id, server_state)
        
        sync_state = self.sync_states[user_id]
        
        # Compare checksums
        client_checksum = self._calculate_checksum(client_state)
        server_checksum = self._calculate_checksum(server_state)
        
        if client_checksum == server_checksum:
            # States are in sync
            return {
                'synced': True,
                'sync_id': sync_state['sync_id'],
                'state': server_state,
                'message': 'States are synchronized'
            }
        
        # Merge states (server wins conflicts)
        merged_state = self._merge_states(client_state, server_state)
        
        # Update sync state
        sync_state['game_state'] = merged_state
        sync_state['last_sync'] = datetime.now().isoformat()
        sync_state['version'] += 1
        sync_state['checksum'] = self._calculate_checksum(merged_state)
        
        return {
            'synced': True,
            'sync_id': sync_state['sync_id'],
            'state': merged_state,
            'version': sync_state['version'],
            'conflicts_resolved': True,
            'message': 'States merged successfully'
        }
    
    def _merge_states(self, client_state: Dict, server_state: Dict) -> Dict:
        """Merge client and server states (server wins conflicts)"""
        merged = server_state.copy()
        
        # Merge non-conflicting fields
        for key, value in client_state.items():
            if key not in server_state:
                merged[key] = value
            elif isinstance(value, (int, float)) and isinstance(server_state[key], (int, float)):
                # Use maximum for numeric values
                merged[key] = max(value, server_state[key])
        
        return merged
    
    def _calculate_checksum(self, state: Dict) -> str:
        """Calculate checksum for state"""
        state_str = json.dumps(state, sort_keys=True)
        return hashlib.md5(state_str.encode()).hexdigest()
    
    def register_peer(self, user_id: str, peer_info: Dict) -> Dict:
        """Register peer for download"""
        if user_id not in self.peer_connections:
            self.peer_connections[user_id] = []
        
        peer_id = peer_info.get('peer_id', str(uuid.uuid4()))
        peer_info['peer_id'] = peer_id
        peer_info['registered_at'] = datetime.now().isoformat()
        
        self.peer_connections[user_id].append(peer_info)
        
        return {
            'success': True,
            'peer_id': peer_id,
            'peers_count': len(self.peer_connections[user_id])
        }
    
    def get_download_peers(self, resource_id: str, user_id: str, count: int = 3) -> List[Dict]:
        """Get peers for download (double or triple)"""
        if resource_id not in self.download_peers:
            self.download_peers[resource_id] = []
        
        # Get available peers (exclude requesting user)
        available_peers = [
            p for p in self.download_peers[resource_id]
            if p.get('user_id') != user_id and p.get('status') == 'available'
        ]
        
        # Return requested number of peers (up to available)
        selected_peers = available_peers[:count]
        
        return {
            'resource_id': resource_id,
            'peers': selected_peers,
            'peers_count': len(selected_peers),
            'requested_count': count
        }
    
    def add_download_peer(self, resource_id: str, peer_info: Dict) -> Dict:
        """Add peer to download pool"""
        if resource_id not in self.download_peers:
            self.download_peers[resource_id] = []
        
        peer_info['added_at'] = datetime.now().isoformat()
        peer_info['status'] = 'available'
        self.download_peers[resource_id].append(peer_info)
        
        return {
            'success': True,
            'resource_id': resource_id,
            'total_peers': len(self.download_peers[resource_id])
        }

