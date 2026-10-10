"""
Timepocket Real-Time Sync System
Three views: Past, Present, Future with real-time synchronization
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
import threading
import time

class TimepocketRealtimeSync:
    """Real-time synchronization for Timepockets with three time views"""
    
    def __init__(self):
        self.time_views = defaultdict(dict)  # {user_id: {view: data}}
        self.active_syncs = {}  # {user_id: sync_data}
        self.timepocket_states = defaultdict(dict)  # {pocket_id: state_data}
        self.sync_history = defaultdict(list)  # {user_id: [sync_events]}
        self.death_teleports = {}  # {teleport_id: death_teleport_data}
        self._sync_thread = None
        self._running = False
    
    def start_sync_service(self):
        """Start the real-time sync service"""
        if self._running:
            return
        
        self._running = True
        self._sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._sync_thread.start()
    
    def stop_sync_service(self):
        """Stop the real-time sync service"""
        self._running = False
        if self._sync_thread:
            self._sync_thread.join(timeout=1)
    
    def _sync_loop(self):
        """Main sync loop - updates all active time views"""
        while self._running:
            try:
                # Update all active syncs
                for user_id, sync_data in list(self.active_syncs.items()):
                    self._update_time_views(user_id, sync_data)
                
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"[TimepocketRealtimeSync] Error in sync loop: {e}", flush=True)
                time.sleep(1)
    
    def _update_time_views(self, user_id: str, sync_data: Dict[str, Any]):
        """Update time views for a user"""
        current_time = datetime.utcnow()
        pocket_id = sync_data.get('pocket_id')
        
        if not pocket_id:
            return
        
        # Get timepocket state
        pocket_state = self.timepocket_states.get(pocket_id, {})
        
        # Update three views
        self.time_views[user_id] = {
            'past': self._get_past_view(pocket_state, current_time),
            'present': self._get_present_view(pocket_state, current_time),
            'future': self._get_future_view(pocket_state, current_time),
            'last_sync': current_time.isoformat(),
            'pocket_id': pocket_id
        }
        
        # Log sync event
        self.sync_history[user_id].append({
            'timestamp': current_time.isoformat(),
            'view': 'all',
            'pocket_id': pocket_id
        })
    
    def _get_past_view(self, pocket_state: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
        """Get past time view"""
        past_time = current_time - timedelta(hours=1)
        return {
            'time_period': 'past',
            'timestamp': past_time.isoformat(),
            'events': pocket_state.get('past_events', []),
            'battle_state': pocket_state.get('past_battle_state', {}),
            'intelligence_level': pocket_state.get('past_intelligence', 100),
            'active_players': pocket_state.get('past_players', []),
            'timepocket_status': 'active',
            'view_time': past_time.isoformat()
        }
    
    def _get_present_view(self, pocket_state: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
        """Get present time view"""
        return {
            'time_period': 'present',
            'timestamp': current_time.isoformat(),
            'events': pocket_state.get('present_events', []),
            'battle_state': pocket_state.get('present_battle_state', {}),
            'intelligence_level': pocket_state.get('present_intelligence', 100),
            'active_players': pocket_state.get('present_players', []),
            'timepocket_status': pocket_state.get('status', 'active'),
            'view_time': current_time.isoformat()
        }
    
    def _get_future_view(self, pocket_state: Dict[str, Any], current_time: datetime) -> Dict[str, Any]:
        """Get future time view"""
        future_time = current_time + timedelta(hours=1)
        return {
            'time_period': 'future',
            'timestamp': future_time.isoformat(),
            'events': pocket_state.get('future_events', []),
            'battle_state': pocket_state.get('future_battle_state', {}),
            'intelligence_level': pocket_state.get('future_intelligence', 100),
            'active_players': pocket_state.get('future_players', []),
            'timepocket_status': 'predicted',
            'view_time': future_time.isoformat()
        }
    
    def start_sync(self, user_id: str, pocket_id: str, battle_id: str) -> Dict[str, Any]:
        """Start real-time sync for a user"""
        self.active_syncs[user_id] = {
            'pocket_id': pocket_id,
            'battle_id': battle_id,
            'started_at': datetime.utcnow().isoformat(),
            'active': True
        }
        
        # Initialize timepocket state if not exists
        if pocket_id not in self.timepocket_states:
            self.timepocket_states[pocket_id] = {
                'pocket_id': pocket_id,
                'battle_id': battle_id,
                'past_events': [],
                'present_events': [],
                'future_events': [],
                'past_battle_state': {},
                'present_battle_state': {},
                'future_battle_state': {},
                'past_intelligence': 100,
                'present_intelligence': 100,
                'future_intelligence': 100,
                'past_players': [],
                'present_players': [],
                'future_players': [],
                'status': 'active'
            }
        
        # Start sync service if not running
        if not self._running:
            self.start_sync_service()
        
        # Initial update
        self._update_time_views(user_id, self.active_syncs[user_id])
        
        return {
            'success': True,
            'sync_started': True,
            'pocket_id': pocket_id,
            'views': self.time_views.get(user_id, {})
        }
    
    def stop_sync(self, user_id: str) -> Dict[str, Any]:
        """Stop real-time sync for a user"""
        if user_id in self.active_syncs:
            del self.active_syncs[user_id]
        
        return {
            'success': True,
            'sync_stopped': True
        }
    
    def get_time_views(self, user_id: str) -> Dict[str, Any]:
        """Get current time views for a user"""
        views = self.time_views.get(user_id, {})
        
        if not views and user_id in self.active_syncs:
            # Update if sync is active but views not initialized
            self._update_time_views(user_id, self.active_syncs[user_id])
            views = self.time_views.get(user_id, {})
        
        return {
            'success': True,
            'views': views,
            'sync_active': user_id in self.active_syncs
        }
    
    def update_timepocket_state(self, pocket_id: str, state_updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update timepocket state (called by battle system)"""
        if pocket_id not in self.timepocket_states:
            self.timepocket_states[pocket_id] = {}
        
        # Update present state
        if 'present_events' in state_updates:
            self.timepocket_states[pocket_id].setdefault('present_events', []).extend(state_updates['present_events'])
        
        if 'present_battle_state' in state_updates:
            self.timepocket_states[pocket_id]['present_battle_state'] = state_updates['present_battle_state']
        
        if 'present_intelligence' in state_updates:
            self.timepocket_states[pocket_id]['present_intelligence'] = state_updates['present_intelligence']
        
        if 'present_players' in state_updates:
            self.timepocket_states[pocket_id]['present_players'] = state_updates['present_players']
        
        # Move present events to past after some time
        # This would be handled by time-based logic
        
        return {
            'success': True,
            'pocket_id': pocket_id,
            'updated': True
        }
    
    def create_death_teleport(self, teleport_id: str, battle_id: str, 
                              from_position: Dict[str, float],
                              death_effect: str = 'instant') -> Dict[str, Any]:
        """Create a Teleport to Death"""
        death_teleport = {
            'teleport_id': teleport_id,
            'battle_id': battle_id,
            'from_position': from_position,
            'to_position': {'x': 0, 'y': 0, 'z': -999},  # Death coordinates
            'death_effect': death_effect,  # instant, slow, dramatic
            'created_at': datetime.utcnow().isoformat(),
            'active': True,
            'uses': 0,
            'max_uses': 1,  # Can only be used once
            'death_message': 'Teleported to death',
            'respawn_time_seconds': 30
        }
        
        self.death_teleports[teleport_id] = death_teleport
        
        return {
            'success': True,
            'death_teleport': death_teleport,
            'message': 'Death teleport created - Use with caution!'
        }
    
    def use_death_teleport(self, teleport_id: str, user_id: str) -> Dict[str, Any]:
        """Use Teleport to Death"""
        if teleport_id not in self.death_teleports:
            return {'success': False, 'error': 'Death teleport not found'}
        
        death_teleport = self.death_teleports[teleport_id]
        
        if not death_teleport['active']:
            return {'success': False, 'error': 'Death teleport inactive'}
        
        if death_teleport['uses'] >= death_teleport['max_uses']:
            return {'success': False, 'error': 'Death teleport already used'}
        
        death_teleport['uses'] += 1
        death_teleport['active'] = False
        
        return {
            'success': True,
            'death_teleport': death_teleport,
            'teleport': {
                'user_id': user_id,
                'from': death_teleport['from_position'],
                'to': death_teleport['to_position'],
                'timestamp': datetime.utcnow().isoformat(),
                'death_effect': death_teleport['death_effect'],
                'respawn_time': death_teleport['respawn_time_seconds']
            },
            'message': f'Teleported to death! Respawn in {death_teleport["respawn_time_seconds"]} seconds'
        }
    
    def get_sync_status(self, user_id: str) -> Dict[str, Any]:
        """Get sync status for a user"""
        sync_data = self.active_syncs.get(user_id, {})
        views = self.time_views.get(user_id, {})
        
        return {
            'success': True,
            'sync_active': user_id in self.active_syncs,
            'pocket_id': sync_data.get('pocket_id'),
            'started_at': sync_data.get('started_at'),
            'has_views': bool(views),
            'last_sync': views.get('last_sync') if views else None
        }


# Global instance
timepocket_realtime = TimepocketRealtimeSync()

