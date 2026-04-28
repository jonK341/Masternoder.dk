"""
Enhanced Point Tracker
Advanced tracking system for point creation and counting
"""
import os
import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class EnhancedPointTracker:
    """Enhanced point tracking with extended time and detailed counting"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.tracker_file = os.path.join(self.base_dir, 'logs', 'point_tracker', 'tracker.json')
        self.load_data()
    
    def load_data(self):
        """Load tracker data"""
        os.makedirs(os.path.dirname(self.tracker_file), exist_ok=True)
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = self._default_data()
        else:
            self.data = self._default_data()
            self.save_data()
    
    def _default_data(self) -> Dict:
        """Default tracker data"""
        return {
            'point_sessions': {},
            'generator_sessions': {},
            'total_points_created': 0,
            'total_time_tracked': 0,
            'extended_sessions': 0,
            'last_update': None
        }
    
    def save_data(self):
        """Save tracker data"""
        try:
            self.data['last_update'] = datetime.now().isoformat()
            with open(self.tracker_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving tracker data: {e}")
    
    def start_generator_session(self, user_id: str, extended_time: bool = True) -> Dict:
        """Start a generator session with extended point creation time"""
        try:
            session_id = f"gen_{user_id}_{int(time.time())}"
            session = {
                'session_id': session_id,
                'user_id': user_id,
                'started_at': datetime.now().isoformat(),
                'extended_time': extended_time,
                'duration_minutes': 60 if extended_time else 30,
                'points_created': 0,
                'point_history': [],
                'active': True
            }
            
            self.data['generator_sessions'][session_id] = session
            self.save_data()
            
            return {
                'success': True,
                'session_id': session_id,
                'duration_minutes': session['duration_minutes'],
                'extended_time': extended_time
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def track_point_creation(self, session_id: str, point_type: str, amount: float, source: str = 'generator') -> Dict:
        """Track point creation during session"""
        try:
            if session_id not in self.data['generator_sessions']:
                return {'success': False, 'error': 'Session not found'}
            
            session = self.data['generator_sessions'][session_id]
            if not session.get('active'):
                return {'success': False, 'error': 'Session not active'}
            
            # Add to point history
            point_entry = {
                'point_type': point_type,
                'amount': amount,
                'source': source,
                'timestamp': datetime.now().isoformat()
            }
            session['point_history'].append(point_entry)
            session['points_created'] += amount
            self.data['total_points_created'] += amount
            
            self.save_data()
            
            return {
                'success': True,
                'session_points': session['points_created'],
                'total_points': self.data['total_points_created'],
                'entry': point_entry
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_session_stats(self, session_id: str) -> Dict:
        """Get statistics for a session"""
        try:
            if session_id not in self.data['generator_sessions']:
                return {'success': False, 'error': 'Session not found'}
            
            session = self.data['generator_sessions'][session_id]
            
            # Calculate stats
            point_types = {}
            for entry in session.get('point_history', []):
                pt = entry['point_type']
                point_types[pt] = point_types.get(pt, 0) + entry['amount']
            
            started = datetime.fromisoformat(session['started_at'])
            elapsed = (datetime.now() - started).total_seconds() / 60
            
            return {
                'success': True,
                'session': {
                    'session_id': session_id,
                    'user_id': session['user_id'],
                    'started_at': session['started_at'],
                    'elapsed_minutes': round(elapsed, 2),
                    'duration_minutes': session['duration_minutes'],
                    'remaining_minutes': max(0, session['duration_minutes'] - elapsed),
                    'points_created': session['points_created'],
                    'point_types': point_types,
                    'entry_count': len(session.get('point_history', [])),
                    'active': session.get('active', False)
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def extend_session_time(self, session_id: str, additional_minutes: int = 30) -> Dict:
        """Extend session time for more point creation"""
        try:
            if session_id not in self.data['generator_sessions']:
                return {'success': False, 'error': 'Session not found'}
            
            session = self.data['generator_sessions'][session_id]
            session['duration_minutes'] += additional_minutes
            self.data['extended_sessions'] += 1
            self.save_data()
            
            return {
                'success': True,
                'new_duration': session['duration_minutes'],
                'additional_minutes': additional_minutes
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_tracking_stats(self) -> Dict:
        """Get comprehensive tracking statistics"""
        try:
            active_sessions = sum(1 for s in self.data['generator_sessions'].values() if s.get('active'))
            total_sessions = len(self.data['generator_sessions'])
            
            # Calculate point breakdown
            point_breakdown = {}
            for session in self.data['generator_sessions'].values():
                for entry in session.get('point_history', []):
                    pt = entry['point_type']
                    point_breakdown[pt] = point_breakdown.get(pt, 0) + entry['amount']
            
            return {
                'success': True,
                'stats': {
                    'total_points_created': self.data['total_points_created'],
                    'total_sessions': total_sessions,
                    'active_sessions': active_sessions,
                    'extended_sessions': self.data['extended_sessions'],
                    'point_breakdown': point_breakdown,
                    'average_points_per_session': (
                        self.data['total_points_created'] / total_sessions 
                        if total_sessions > 0 else 0
                    )
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Global instance
enhanced_point_tracker = EnhancedPointTracker()
