"""
Battle Arena Event Handlers
Event handlers for gear operations
"""
from typing import Dict, Any, Callable, List
from datetime import datetime
from collections import defaultdict
import logging

logger = logging.getLogger('battle_arena.events')


class BattleArenaEventHandler:
    """Event handler system for battle arena gear operations"""
    
    def __init__(self):
        self.event_handlers = defaultdict(list)
        self.event_history = []
    
    def register_handler(self, event_type: str, handler: Callable):
        """Register an event handler"""
        self.event_handlers[event_type].append(handler)
        logger.info(f"Registered handler for event: {event_type}")
    
    def emit(self, event_type: str, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Emit an event and execute all registered handlers"""
        event = {
            'event_type': event_type,
            'data': data,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        self.event_history.append(event)
        
        results = []
        handlers = self.event_handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                result = handler(data)
                results.append({
                    'handler': handler.__name__,
                    'result': result,
                    'success': True
                })
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__}: {e}")
                results.append({
                    'handler': handler.__name__,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def get_event_history(self, event_type: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get event history"""
        if event_type:
            return [e for e in self.event_history if e['event_type'] == event_type][-limit:]
        return self.event_history[-limit:]


# Global event handler instance
battle_arena_event_handler = BattleArenaEventHandler()


# Event handlers for gear operations

def handle_gear_equipped(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle gear equipped event"""
    logger.info(f"Gear equipped: {data.get('gear_id')} for user {data.get('user_id')}")
    return {'event': 'gear_equipped', 'handled': True}


def handle_gear_unequipped(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle gear unequipped event"""
    logger.info(f"Gear unequipped: slot {data.get('slot')} for user {data.get('user_id')}")
    return {'event': 'gear_unequipped', 'handled': True}


def handle_stats_calculated(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle stats calculated event"""
    logger.info(f"Stats calculated for gear {data.get('gear_id')} and user {data.get('user_id')}")
    return {'event': 'stats_calculated', 'handled': True}


def handle_gear_generated(data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle gear generated event"""
    logger.info(f"Gear generated: {data.get('gear_id')} for user {data.get('user_id')}")
    return {'event': 'gear_generated', 'handled': True}


# Register default event handlers
battle_arena_event_handler.register_handler('gear_equipped', handle_gear_equipped)
battle_arena_event_handler.register_handler('gear_unequipped', handle_gear_unequipped)
battle_arena_event_handler.register_handler('stats_calculated', handle_stats_calculated)
battle_arena_event_handler.register_handler('gear_generated', handle_gear_generated)

