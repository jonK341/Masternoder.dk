"""
Autoplay & Recording System
Record battles as .mp4 files with four underlines naming convention
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
import os
import uuid

# Ensure recordings directory exists
if not os.path.exists('recordings'):
    os.makedirs('recordings', exist_ok=True)

class AutoplayRecording:
    """Autoplay and Recording System for Battle Videos"""
    
    def __init__(self):
        self.recordings = defaultdict(list)  # {user_id: [recording_data]}
        self.autoplay_sessions = defaultdict(dict)  # {user_id: session_data}
        self.recording_queue = []  # Queue of recordings to process
        self.output_directory = 'recordings'  # Output directory for .mp4 files
    
    def start_autoplay_recording(
        self,
        user_id: str,
        battle_id: str,
        duration_seconds: int = 60
    ) -> Dict[str, Any]:
        """Start autoplay recording session"""
        session_id = f"autoplay_{datetime.utcnow().timestamp()}"
        
        # Generate filename with four underlines
        filename = self._generate_filename(user_id, battle_id)
        
        session = {
            'session_id': session_id,
            'user_id': user_id,
            'battle_id': battle_id,
            'filename': filename,
            'status': 'recording',
            'started_at': datetime.utcnow().isoformat(),
            'duration_seconds': duration_seconds,
            'frames_recorded': 0,
            'file_path': os.path.join(self.output_directory, filename)
        }
        
        self.autoplay_sessions[user_id][session_id] = session
        
        return {
            'success': True,
            'session': session,
            'message': f'Autoplay recording started: {filename}'
        }
    
    def stop_autoplay_recording(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Stop autoplay recording and finalize .mp4 file"""
        if user_id not in self.autoplay_sessions or session_id not in self.autoplay_sessions[user_id]:
            return {'success': False, 'error': 'Session not found'}
        
        session = self.autoplay_sessions[user_id][session_id]
        session['status'] = 'completed'
        session['stopped_at'] = datetime.utcnow().isoformat()
        session['duration_actual'] = (
            datetime.fromisoformat(session['stopped_at']) - 
            datetime.fromisoformat(session['started_at'])
        ).total_seconds()
        
        # Create recording entry
        recording = {
            'recording_id': f"recording_{datetime.utcnow().timestamp()}",
            'session_id': session_id,
            'user_id': user_id,
            'battle_id': session['battle_id'],
            'filename': session['filename'],
            'file_path': session['file_path'],
            'duration_seconds': session['duration_actual'],
            'frames_recorded': session['frames_recorded'],
            'created_at': datetime.utcnow().isoformat(),
            'status': 'ready',
            'file_size_mb': 0  # Will be calculated when file is created
        }
        
        self.recordings[user_id].append(recording)
        
        # Add to processing queue
        self.recording_queue.append(recording)
        
        # Remove from active sessions
        del self.autoplay_sessions[user_id][session_id]
        
        return {
            'success': True,
            'recording': recording,
            'message': f'Recording completed: {session["filename"]}'
        }
    
    def _generate_filename(self, user_id: str, battle_id: str) -> str:
        """Generate filename with four underlines convention"""
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        # Format: user_id____battle_id____timestamp____recording.mp4
        filename = f"{user_id}____{battle_id}____{timestamp}____recording.mp4"
        return filename
    
    def get_user_recordings(self, user_id: str) -> Dict[str, Any]:
        """Get user's recordings"""
        recordings = self.recordings.get(user_id, [])
        active_sessions = list(self.autoplay_sessions.get(user_id, {}).values())
        
        return {
            'success': True,
            'recordings': recordings,
            'active_sessions': active_sessions,
            'total_recordings': len(recordings),
            'active_sessions_count': len(active_sessions)
        }
    
    def get_recording(self, user_id: str, recording_id: str) -> Optional[Dict[str, Any]]:
        """Get specific recording"""
        recordings = self.recordings.get(user_id, [])
        for recording in recordings:
            if recording['recording_id'] == recording_id:
                return recording
        return None
    
    def download_recording(self, user_id: str, recording_id: str) -> Dict[str, Any]:
        """Get download information for recording"""
        recording = self.get_recording(user_id, recording_id)
        
        if not recording:
            return {'success': False, 'error': 'Recording not found'}
        
        return {
            'success': True,
            'recording': recording,
            'download_url': f"/api/battle/recordings/{recording_id}/download",
            'filename': recording['filename']
        }


# Global instance
autoplay_recording = AutoplayRecording()

