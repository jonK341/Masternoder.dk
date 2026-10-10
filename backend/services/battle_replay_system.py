"""
Battle Replay System
Records, stores, and replays battle data
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
import uuid

try:
    from backend.services.autoplay_recording import AutoplayRecording
    autoplay_recording = AutoplayRecording()
except ImportError:
    autoplay_recording = None


class BattleReplaySystem:
    """System for recording and replaying battles"""
    
    def __init__(self, data_dir: str = 'data/battle_replays'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # In-memory storage
        self.replays = {}  # replay_id -> replay_data
        self.battle_replays = {}  # battle_id -> [replay_ids]
        self.user_replays = {}  # user_id -> [replay_ids]
    
    def record_battle(self, battle_id: str, battle_data: Dict[str, Any], 
                     actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Record a battle for replay
        
        Args:
            battle_id: Battle identifier
            battle_data: Battle metadata
            actions: List of battle actions
            
        Returns:
            Replay recording result
        """
        replay_id = f"replay_{battle_id}_{int(datetime.utcnow().timestamp())}"
        
        replay_data = {
            'replay_id': replay_id,
            'battle_id': battle_id,
            'user1_id': battle_data.get('user1_id') or battle_data.get('clan1_id'),
            'user2_id': battle_data.get('user2_id') or battle_data.get('clan2_id'),
            'battle_type': battle_data.get('battle_type', 'quick'),
            'recorded_at': datetime.utcnow().isoformat(),
            'battle_data': battle_data,
            'actions': actions,
            'duration': battle_data.get('duration', 0),
            'winner': battle_data.get('winner'),
            'final_scores': {
                'user1_score': battle_data.get('clan1_score', 0),
                'user2_score': battle_data.get('clan2_score', 0)
            }
        }
        
        # Store in memory
        self.replays[replay_id] = replay_data
        
        # Index by battle
        if battle_id not in self.battle_replays:
            self.battle_replays[battle_id] = []
        self.battle_replays[battle_id].append(replay_id)
        
        # Index by users
        user1_id = replay_data['user1_id']
        user2_id = replay_data['user2_id']
        
        if user1_id:
            if user1_id not in self.user_replays:
                self.user_replays[user1_id] = []
            self.user_replays[user1_id].append(replay_id)
        
        if user2_id:
            if user2_id not in self.user_replays:
                self.user_replays[user2_id] = []
            self.user_replays[user2_id].append(replay_id)
        
        # Save to file
        self._save_replay(replay_id, replay_data)
        
        return {
            'success': True,
            'replay_id': replay_id,
            'message': 'Battle recorded for replay'
        }
    
    def get_replay(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """Get replay data"""
        if replay_id in self.replays:
            return self.replays[replay_id]
        
        # Try to load from file
        return self._load_replay(replay_id)
    
    def get_user_replays(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get all replays for a user"""
        replay_ids = self.user_replays.get(user_id, [])[:limit]
        replays = []
        
        for replay_id in replay_ids:
            replay = self.get_replay(replay_id)
            if replay:
                replays.append(replay)
        
        return replays
    
    def get_battle_replays(self, battle_id: str) -> List[Dict[str, Any]]:
        """Get all replays for a battle"""
        replay_ids = self.battle_replays.get(battle_id, [])
        replays = []
        
        for replay_id in replay_ids:
            replay = self.get_replay(replay_id)
            if replay:
                replays.append(replay)
        
        return replays
    
    def share_replay(self, replay_id: str, share_token: Optional[str] = None) -> Dict[str, Any]:
        """Generate shareable link for replay"""
        if not share_token:
            share_token = str(uuid.uuid4())[:8]
        
        replay = self.get_replay(replay_id)
        if not replay:
            return {'success': False, 'error': 'Replay not found'}
        
        replay['share_token'] = share_token
        replay['shareable'] = True
        replay['shared_at'] = datetime.utcnow().isoformat()
        
        self._save_replay(replay_id, replay)
        
        return {
            'success': True,
            'share_token': share_token,
            'share_url': f'/vidgenerator/battle/replay/{replay_id}?token={share_token}'
        }
    
    def _save_replay(self, replay_id: str, replay_data: Dict[str, Any]) -> bool:
        """Save replay to file"""
        try:
            file_path = os.path.join(self.data_dir, f'{replay_id}.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(replay_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[BattleReplay] Error saving replay {replay_id}: {e}", flush=True)
            return False
    
    def _load_replay(self, replay_id: str) -> Optional[Dict[str, Any]]:
        """Load replay from file"""
        try:
            file_path = os.path.join(self.data_dir, f'{replay_id}.json')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    replay_data = json.load(f)
                    self.replays[replay_id] = replay_data
                    return replay_data
        except Exception as e:
            print(f"[BattleReplay] Error loading replay {replay_id}: {e}", flush=True)
        return None
    
    def delete_replay(self, replay_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a replay (only by owner)"""
        replay = self.get_replay(replay_id)
        if not replay:
            return {'success': False, 'error': 'Replay not found'}
        
        # Check ownership
        if replay['user1_id'] != user_id and replay['user2_id'] != user_id:
            return {'success': False, 'error': 'Not authorized'}
        
        # Remove from memory
        if replay_id in self.replays:
            del self.replays[replay_id]
        
        # Remove from indexes
        battle_id = replay['battle_id']
        if battle_id in self.battle_replays:
            self.battle_replays[battle_id] = [r for r in self.battle_replays[battle_id] if r != replay_id]
        
        user1_id = replay['user1_id']
        user2_id = replay['user2_id']
        if user1_id and user1_id in self.user_replays:
            self.user_replays[user1_id] = [r for r in self.user_replays[user1_id] if r != replay_id]
        if user2_id and user2_id in self.user_replays:
            self.user_replays[user2_id] = [r for r in self.user_replays[user2_id] if r != replay_id]
        
        # Delete file
        try:
            file_path = os.path.join(self.data_dir, f'{replay_id}.json')
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"[BattleReplay] Error deleting replay file: {e}", flush=True)
        
        return {'success': True, 'message': 'Replay deleted'}


# Global instance
battle_replay_system = BattleReplaySystem()
