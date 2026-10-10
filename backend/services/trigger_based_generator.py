"""
Trigger-Based Generator System
Converts instant generation to trigger-based behavior with pointer catching
"""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import uuid

class TriggerBasedGenerator:
    """Generator system with trigger-based behavior instead of instant execution"""
    
    def __init__(self):
        self.pending_triggers = {}  # trigger_id -> trigger_data
        self.trigger_handlers = {}  # trigger_type -> handler_function
        self.pointer_registry = {}  # pointer_id -> pointer_data
        self._initialize_handlers()
    
    def _initialize_handlers(self):
        """Initialize trigger handlers"""
        self.trigger_handlers = {
            'video_generation': self._handle_video_generation,
            'quick_battle': self._handle_quick_battle,
            'point_award': self._handle_point_award,
            'energy_check': self._handle_energy_check,
            'skill_unlock': self._handle_skill_unlock
        }
    
    def register_trigger(self, trigger_type: str, data: Dict[str, Any], 
                        expected_pointers: List[str] = None) -> str:
        """Register a trigger that waits for expected pointers"""
        trigger_id = str(uuid.uuid4())
        
        self.pending_triggers[trigger_id] = {
            'id': trigger_id,
            'type': trigger_type,
            'data': data,
            'expected_pointers': expected_pointers or [],
            'received_pointers': [],
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'handler': self.trigger_handlers.get(trigger_type)
        }
        
        return trigger_id
    
    def catch_pointer(self, pointer_id: str, pointer_data: Dict[str, Any]) -> List[str]:
        """Catch a pointer and check if it matches any pending triggers"""
        self.pointer_registry[pointer_id] = {
            'id': pointer_id,
            'data': pointer_data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        triggered = []
        
        # Check all pending triggers
        for trigger_id, trigger in list(self.pending_triggers.items()):
            if trigger['status'] != 'pending':
                continue
            
            # Check if this pointer matches expected pointers
            if pointer_id in trigger['expected_pointers']:
                trigger['received_pointers'].append(pointer_id)
                
                # Check if all expected pointers received
                if set(trigger['received_pointers']) >= set(trigger['expected_pointers']):
                    # Execute trigger
                    result = self._execute_trigger(trigger_id)
                    if result:
                        triggered.append(trigger_id)
        
        return triggered
    
    def _execute_trigger(self, trigger_id: str) -> bool:
        """Execute a trigger when all pointers are received"""
        trigger = self.pending_triggers.get(trigger_id)
        if not trigger or trigger['status'] != 'pending':
            return False
        
        trigger['status'] = 'executing'
        
        try:
            handler = trigger['handler']
            if handler:
                result = handler(trigger['data'], trigger['received_pointers'])
                trigger['status'] = 'completed'
                trigger['result'] = result
                return True
            else:
                trigger['status'] = 'no_handler'
                return False
        except Exception as e:
            trigger['status'] = 'error'
            trigger['error'] = str(e)
            return False
    
    def _handle_video_generation(self, data: Dict, pointers: List[str]) -> Dict:
        """Handle video generation trigger"""
        # Instead of instant generation, queue it with trigger
        return {
            'success': True,
            'trigger_type': 'video_generation',
            'message': 'Video generation queued via trigger system',
            'pointers_received': pointers,
            'data': data
        }
    
    def _handle_quick_battle(self, data: Dict, pointers: List[str]) -> Dict:
        """Handle quick battle trigger"""
        # Instead of instant battle, queue it with trigger
        return {
            'success': True,
            'trigger_type': 'quick_battle',
            'message': 'Quick battle queued via trigger system',
            'pointers_received': pointers,
            'data': data
        }
    
    def _handle_point_award(self, data: Dict, pointers: List[str]) -> Dict:
        """Handle point award trigger"""
        return {
            'success': True,
            'trigger_type': 'point_award',
            'points': data.get('points', 0),
            'pointers_received': pointers
        }
    
    def _handle_energy_check(self, data: Dict, pointers: List[str]) -> Dict:
        """Handle energy check trigger"""
        return {
            'success': True,
            'trigger_type': 'energy_check',
            'energy_status': 'checked',
            'pointers_received': pointers
        }
    
    def _handle_skill_unlock(self, data: Dict, pointers: List[str]) -> Dict:
        """Handle skill unlock trigger"""
        return {
            'success': True,
            'trigger_type': 'skill_unlock',
            'skill_id': data.get('skill_id'),
            'pointers_received': pointers
        }
    
    def get_trigger_status(self, trigger_id: str) -> Optional[Dict]:
        """Get status of a trigger"""
        return self.pending_triggers.get(trigger_id)
    
    def list_pending_triggers(self, user_id: str = None) -> List[Dict]:
        """List all pending triggers"""
        triggers = []
        for trigger_id, trigger in self.pending_triggers.items():
            if trigger['status'] == 'pending':
                if user_id is None or trigger['data'].get('user_id') == user_id:
                    triggers.append({
                        'id': trigger_id,
                        'type': trigger['type'],
                        'status': trigger['status'],
                        'expected_pointers': trigger['expected_pointers'],
                        'received_pointers': trigger['received_pointers'],
                        'created_at': trigger['created_at']
                    })
        return triggers

# Global instance
trigger_based_generator = TriggerBasedGenerator()

