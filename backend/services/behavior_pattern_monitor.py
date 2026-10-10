"""
Behavior Pattern Monitor
Monitors changes in behavior patterns and saves to encrypted JSON
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json

try:
    from backend.services.encrypted_json_storage import encrypted_json_storage
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
except ImportError:
    encrypted_json_storage = None
    advanced_intelligent_calculator = None


class BehaviorPatternMonitor:
    """
    Monitors behavior patterns and detects changes
    Saves data to encrypted JSON
    """
    
    def __init__(self):
        """Initialize behavior pattern monitor"""
        self.pattern_history = defaultdict(deque)  # {user_id: deque of patterns}
        self.change_detections = defaultdict(list)  # {user_id: [detections]}
        self.max_history = 1000  # Keep last 1000 patterns
    
    def record_behavior(self, user_id: str, behavior_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Record behavior pattern
        
        Args:
            user_id: User identifier
            behavior_data: Behavior data to record
            
        Returns:
            Recording result
        """
        try:
            timestamp = datetime.utcnow()
            
            pattern_entry = {
                'timestamp': timestamp.isoformat(),
                'behavior_data': behavior_data,
                'pattern_id': self._generate_pattern_id(user_id, timestamp)
            }
            
            # Add to history
            self.pattern_history[user_id].append(pattern_entry)
            
            # Keep only last N entries
            if len(self.pattern_history[user_id]) > self.max_history:
                self.pattern_history[user_id].popleft()
            
            # Detect changes
            changes = self._detect_changes(user_id, pattern_entry)
            
            if changes:
                self.change_detections[user_id].extend(changes)
                # Save to encrypted JSON
                self._save_to_encrypted_json(user_id, changes)
            
            return {
                'success': True,
                'pattern_id': pattern_entry['pattern_id'],
                'changes_detected': len(changes) if changes else 0,
                'changes': changes
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _detect_changes(self, user_id: str, new_pattern: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect changes in behavior patterns"""
        changes = []
        
        if len(self.pattern_history[user_id]) < 2:
            return changes
        
        # Get recent patterns
        recent_patterns = list(self.pattern_history[user_id])[-10:]
        if len(recent_patterns) < 2:
            return changes
        
        # Compare with previous patterns
        previous_pattern = recent_patterns[-2]
        current_behavior = new_pattern['behavior_data']
        previous_behavior = previous_pattern['behavior_data']
        
        # Detect significant changes
        for key, current_value in current_behavior.items():
            previous_value = previous_behavior.get(key)
            
            if previous_value is None:
                continue
            
            # Calculate change percentage
            if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
                if previous_value != 0:
                    change_percentage = abs((current_value - previous_value) / previous_value) * 100
                    
                    # Significant change threshold (20%)
                    if change_percentage > 20:
                        changes.append({
                            'type': 'behavior_change',
                            'field': key,
                            'previous_value': previous_value,
                            'current_value': current_value,
                            'change_percentage': change_percentage,
                            'timestamp': new_pattern['timestamp'],
                            'severity': 'high' if change_percentage > 50 else 'medium'
                        })
        
        return changes
    
    def _save_to_encrypted_json(self, user_id: str, changes: List[Dict[str, Any]]):
        """Save behavior changes to encrypted JSON"""
        if not encrypted_json_storage:
            return
        
        try:
            # Get existing data
            existing = encrypted_json_storage.load_encrypted_json('behavior_patterns', user_id)
            
            if existing.get('success'):
                data = existing.get('data', {})
            else:
                data = {
                    'user_id': user_id,
                    'patterns': [],
                    'changes': [],
                    'statistics': {}
                }
            
            # Add new changes
            data['changes'].extend(changes)
            data['last_updated'] = datetime.utcnow().isoformat()
            
            # Update statistics
            data['statistics'] = {
                'total_changes': len(data['changes']),
                'high_severity': len([c for c in data['changes'] if c.get('severity') == 'high']),
                'medium_severity': len([c for c in data['changes'] if c.get('severity') == 'medium']),
                'last_change': changes[-1]['timestamp'] if changes else None
            }
            
            # Save encrypted
            result = encrypted_json_storage.save_encrypted_json('behavior_patterns', data, user_id)
            
            if result.get('success'):
                print(f"[BehaviorMonitor] Saved behavior patterns for {user_id}", flush=True)
        except Exception as e:
            print(f"[BehaviorMonitor] Error saving to encrypted JSON: {e}", flush=True)
    
    def _generate_pattern_id(self, user_id: str, timestamp: datetime) -> str:
        """Generate pattern ID"""
        import hashlib
        data = f"{user_id}_{timestamp.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_behavior_changes(self, user_id: str) -> Dict[str, Any]:
        """Get behavior changes for a user"""
        try:
            if not encrypted_json_storage:
                return {'success': False, 'error': 'Encrypted storage not available'}
            
            result = encrypted_json_storage.load_encrypted_json('behavior_patterns', user_id)
            
            if result.get('success'):
                return {
                    'success': True,
                    'user_id': user_id,
                    'data': result.get('data', {}),
                    'metadata': result.get('metadata', {})
                }
            else:
                return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
behavior_pattern_monitor = BehaviorPatternMonitor()

