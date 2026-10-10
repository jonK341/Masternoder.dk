"""
Scaling Event System - Event-driven architecture for 1.3 billion users
Uses event handlers, viewers, and listeners for distributed processing
"""
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict, deque
import uuid
import threading
import queue
import time

try:
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    CALCULATOR_AVAILABLE = True
except ImportError:
    advanced_intelligent_calculator = None
    CALCULATOR_AVAILABLE = False


class EventViewer:
    """Viewer - Observes and processes events without modifying state"""
    
    def __init__(self, viewer_id: str, event_types: List[str], processor: Callable):
        self.viewer_id = viewer_id
        self.event_types = event_types
        self.processor = processor
        self.processed_count = 0
        self.last_processed = None
    
    def view(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """View and process event (read-only operation)"""
        if event.get('type') not in self.event_types:
            return {'viewed': False}
        
        try:
            result = self.processor(event)
            self.processed_count += 1
            self.last_processed = datetime.utcnow().isoformat()
            return {
                'viewed': True,
                'viewer_id': self.viewer_id,
                'result': result,
                'processed_count': self.processed_count
            }
        except Exception as e:
            return {
                'viewed': True,
                'viewer_id': self.viewer_id,
                'error': str(e)
            }


class EventListener:
    """Listener - Listens to events and triggers actions"""
    
    def __init__(self, listener_id: str, event_patterns: List[str], handler: Callable):
        self.listener_id = listener_id
        self.event_patterns = event_patterns
        self.handler = handler
        self.triggered_count = 0
        self.last_triggered = None
        self.active = True
    
    def listen(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Listen to event and trigger handler if pattern matches"""
        if not self.active:
            return {'listened': False, 'reason': 'inactive'}
        
        event_type = event.get('type', '')
        if not any(pattern in event_type for pattern in self.event_patterns):
            return {'listened': False, 'reason': 'pattern_no_match'}
        
        try:
            result = self.handler(event)
            self.triggered_count += 1
            self.last_triggered = datetime.utcnow().isoformat()
            return {
                'listened': True,
                'listener_id': self.listener_id,
                'triggered': True,
                'result': result,
                'triggered_count': self.triggered_count
            }
        except Exception as e:
            return {
                'listened': True,
                'listener_id': self.listener_id,
                'triggered': False,
                'error': str(e)
            }


class ScalingEventHandler:
    """
    Event Handler - Processes events with calculator integration
    Designed for massive scale (1.3 billion users)
    """
    
    def __init__(self, handler_id: str, event_types: List[str], processor: Callable):
        self.handler_id = handler_id
        self.event_types = event_types
        self.processor = processor
        self.processed_count = 0
        self.error_count = 0
        self.last_processed = None
        self.use_calculator = CALCULATOR_AVAILABLE
    
    def handle(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Handle event with calculator integration if available"""
        if event.get('type') not in self.event_types:
            return {'handled': False, 'reason': 'type_not_supported'}
        
        try:
            # Use calculator for calculations if available
            if self.use_calculator and 'calculation' in event.get('type', '').lower():
                try:
                    point_data = event.get('data', {}).get('point_data', {})
                    user_id = event.get('user_id', event.get('data', {}).get('user_id', 'default'))
                    
                    if point_data:
                        calc_result = advanced_intelligent_calculator.calculate_with_intelligence(
                            point_data, user_id
                        )
                        event['calculator_result'] = calc_result
                except Exception as calc_err:
                    print(f"[ScalingEventHandler] Calculator error (non-critical): {calc_err}")
            
            # Process event
            result = self.processor(event)
            self.processed_count += 1
            self.last_processed = datetime.utcnow().isoformat()
            
            return {
                'handled': True,
                'handler_id': self.handler_id,
                'result': result,
                'processed_count': self.processed_count,
                'calculator_used': self.use_calculator and 'calculation' in event.get('type', '').lower()
            }
        except Exception as e:
            self.error_count += 1
            return {
                'handled': False,
                'handler_id': self.handler_id,
                'error': str(e),
                'error_count': self.error_count
            }


class ScalingEventSystem:
    """
    Scaling Event System for 1.3 billion users
    Event-driven architecture with handlers, viewers, and listeners
    Uses calculator for distributed calculations
    """
    
    def __init__(self):
        self.handlers = {}  # {handler_id: EventHandler}
        self.viewers = {}  # {viewer_id: EventViewer}
        self.listeners = {}  # {listener_id: EventListener}
        self.event_queue = queue.Queue(maxsize=1000000)  # Queue for 1M events
        self.event_history = deque(maxlen=10000)  # Last 10K events
        self.stats = {
            'total_events': 0,
            'handled_events': 0,
            'viewed_events': 0,
            'listened_events': 0,
            'error_events': 0,
            'events_per_second': 0
        }
        self.worker_threads = []
        self.max_workers = 100  # Max worker threads
        self.running = False
        self.lock = threading.Lock()
    
    def register_handler(self, handler_id: str, event_types: List[str], 
                        processor: Callable) -> Dict[str, Any]:
        """Register an event handler"""
        handler = ScalingEventHandler(handler_id, event_types, processor)
        self.handlers[handler_id] = handler
        return {
            'success': True,
            'handler_id': handler_id,
            'event_types': event_types
        }
    
    def register_viewer(self, viewer_id: str, event_types: List[str],
                       processor: Callable) -> Dict[str, Any]:
        """Register an event viewer"""
        viewer = EventViewer(viewer_id, event_types, processor)
        self.viewers[viewer_id] = viewer
        return {
            'success': True,
            'viewer_id': viewer_id,
            'event_types': event_types
        }
    
    def register_listener(self, listener_id: str, event_patterns: List[str],
                         handler: Callable) -> Dict[str, Any]:
        """Register an event listener"""
        listener = EventListener(listener_id, event_patterns, handler)
        self.listeners[listener_id] = listener
        return {
            'success': True,
            'listener_id': listener_id,
            'event_patterns': event_patterns
        }
    
    def emit(self, event_type: str, event_data: Dict[str, Any],
            user_id: str = None, priority: int = 5) -> Dict[str, Any]:
        """
        Emit an event (non-blocking, queue-based)
        
        Args:
            event_type: Type of event
            event_data: Event data payload
            user_id: User ID (optional)
            priority: Priority (1-10, higher = more important)
        """
        event = {
            'event_id': str(uuid.uuid4()),
            'type': event_type,
            'data': event_data,
            'user_id': user_id,
            'priority': priority,
            'timestamp': datetime.utcnow().isoformat(),
            'processed': False
        }
        
        try:
            # Try to put in queue (non-blocking)
            self.event_queue.put_nowait((priority, event))
            with self.lock:
                self.stats['total_events'] += 1
            return {
                'success': True,
                'event_id': event['event_id'],
                'queued': True
            }
        except queue.Full:
            # Queue full - handle overflow
            return {
                'success': False,
                'error': 'Event queue full',
                'event_id': event['event_id']
            }
    
    def process_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single event through handlers, viewers, and listeners"""
        results = {
            'event_id': event.get('event_id'),
            'handled_by': [],
            'viewed_by': [],
            'listened_by': [],
            'errors': []
        }
        
        # Process through handlers
        for handler_id, handler in self.handlers.items():
            if event.get('type') in handler.event_types:
                try:
                    result = handler.handle(event)
                    if result.get('handled'):
                        results['handled_by'].append({
                            'handler_id': handler_id,
                            'result': result
                        })
                        with self.lock:
                            self.stats['handled_events'] += 1
                except Exception as e:
                    results['errors'].append({
                        'handler_id': handler_id,
                        'error': str(e)
                    })
        
        # Process through viewers (read-only)
        for viewer_id, viewer in self.viewers.items():
            if event.get('type') in viewer.event_types:
                try:
                    result = viewer.view(event)
                    if result.get('viewed'):
                        results['viewed_by'].append({
                            'viewer_id': viewer_id,
                            'result': result
                        })
                        with self.lock:
                            self.stats['viewed_events'] += 1
                except Exception as e:
                    results['errors'].append({
                        'viewer_id': viewer_id,
                        'error': str(e)
                    })
        
        # Process through listeners
        for listener_id, listener in self.listeners.items():
            try:
                result = listener.listen(event)
                if result.get('listened') and result.get('triggered'):
                    results['listened_by'].append({
                        'listener_id': listener_id,
                        'result': result
                    })
                    with self.lock:
                        self.stats['listened_events'] += 1
            except Exception as e:
                results['errors'].append({
                    'listener_id': listener_id,
                    'error': str(e)
                })
        
        event['processed'] = True
        event['processed_at'] = datetime.utcnow().isoformat()
        self.event_history.append(event)
        
        return results
    
    def worker_thread(self, worker_id: int):
        """Worker thread for processing events from queue"""
        print(f"[ScalingEventSystem] Worker {worker_id} started", flush=True)
        
        while self.running:
            try:
                # Get event from queue (with timeout)
                try:
                    priority, event = self.event_queue.get(timeout=1)
                    result = self.process_event(event)
                    self.event_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as queue_err:
                    print(f"[ScalingEventSystem] Worker {worker_id} queue error: {queue_err}", flush=True)
                    continue
            except Exception as e:
                print(f"[ScalingEventSystem] Worker {worker_id} error: {e}", flush=True)
                with self.lock:
                    self.stats['error_events'] += 1
                import time
                time.sleep(0.1)  # Brief pause before retry
    
    def start_workers(self, num_workers: int = None):
        """Start worker threads for event processing"""
        if self.running:
            return {'success': False, 'error': 'Workers already running'}
        
        num_workers = num_workers or min(self.max_workers, 10)
        self.running = True
        
        for i in range(num_workers):
            thread = threading.Thread(target=self.worker_thread, args=(i,), daemon=True)
            thread.start()
            self.worker_threads.append(thread)
        
        return {
            'success': True,
            'workers_started': num_workers,
            'max_workers': self.max_workers
        }
    
    def stop_workers(self):
        """Stop worker threads"""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.worker_threads:
            thread.join(timeout=5)
        
        self.worker_threads.clear()
        
        return {'success': True, 'workers_stopped': len(self.worker_threads)}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        queue_size = self.event_queue.qsize()
        
        # Calculate events per second (simplified)
        events_per_second = 0
        if len(self.event_history) > 1:
            try:
                first_time = datetime.fromisoformat(self.event_history[0]['timestamp'].replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(self.event_history[-1]['timestamp'].replace('Z', '+00:00'))
                time_diff = (last_time - first_time).total_seconds()
                if time_diff > 0:
                    events_per_second = len(self.event_history) / time_diff
            except:
                pass
        
        return {
            'total_events': self.stats['total_events'],
            'handled_events': self.stats['handled_events'],
            'viewed_events': self.stats['viewed_events'],
            'listened_events': self.stats['listened_events'],
            'error_events': self.stats['error_events'],
            'queue_size': queue_size,
            'queue_max_size': self.event_queue.maxsize,
            'events_per_second': round(events_per_second, 2),
            'handlers_count': len(self.handlers),
            'viewers_count': len(self.viewers),
            'listeners_count': len(self.listeners),
            'workers_running': len([t for t in self.worker_threads if t.is_alive()]),
            'running': self.running,
            'calculator_available': CALCULATOR_AVAILABLE
        }
    
    def calculate_with_calculator(self, user_id: str, point_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate using distributed calculator"""
        if not CALCULATOR_AVAILABLE:
            return {'success': False, 'error': 'Calculator not available'}
        
        try:
            result = advanced_intelligent_calculator.calculate_with_intelligence(
                point_data, user_id
            )
            return {
                'success': True,
                'calculation_id': result.get('calculation_id'),
                'final_calculation': result.get('final_calculation', {}),
                'confidence': result.get('confidence_score', 0)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


# Global instance
scaling_event_system = ScalingEventSystem()

