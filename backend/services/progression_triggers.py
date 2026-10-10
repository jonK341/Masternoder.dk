"""
Progression Triggers System
Tracks and triggers progression events based on stat changes
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import defaultdict
import json

class ProgressionTriggers:
    """Progression triggers system"""
    
    def __init__(self):
        self.progression_history = defaultdict(list)  # {user_id: [progression_events]}
        self.trigger_thresholds = {
            'xp': [100, 500, 1000, 5000, 10000],
            'level': [5, 10, 20, 30, 50],
            'battle_points': [100, 500, 1000, 5000],
            'trophy_points': [50, 200, 500, 1000],
        }
    
    def check_progression(self, user_id: str, stat_type: str, current_value: int) -> Dict[str, Any]:
        """Check progression for a stat"""
        thresholds = self.trigger_thresholds.get(stat_type, [])
        triggered = []
        
        for threshold in thresholds:
            if current_value >= threshold:
                # Check if already triggered
                if not any(e.get('stat_type') == stat_type and e.get('threshold') == threshold 
                          for e in self.progression_history[user_id]):
                    event = {
                        'stat_type': stat_type,
                        'threshold': threshold,
                        'value': current_value,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    self.progression_history[user_id].append(event)
                    triggered.append(event)
        
        return {
            'success': True,
            'user_id': user_id,
            'stat_type': stat_type,
            'current_value': current_value,
            'triggered': triggered,
            'next_threshold': next((t for t in thresholds if t > current_value), None)
        }
    
    def check_all_stats(self, user_id: str) -> Dict[str, Any]:
        """Check progression for all stats"""
        # This would typically get stats from unified points system
        # For now, return structure
        return {
            'success': True,
            'user_id': user_id,
            'checked_stats': list(self.trigger_thresholds.keys()),
            'message': 'Stats checked (implement full stat retrieval)'
        }
    
    def get_progression_history(self, user_id: str) -> Dict[str, Any]:
        """Get progression history"""
        return {
            'success': True,
            'user_id': user_id,
            'history': self.progression_history.get(user_id, []),
            'total_events': len(self.progression_history.get(user_id, []))
        }

progression_triggers = ProgressionTriggers()
