"""
Generator Timeout Handler - Manages timeout and event triggers for video generation
"""
import time
import threading
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta

class GeneratorTimeoutHandler:
    """Manages timeout, error handling, and event triggers for video generation"""
    
    def __init__(self, max_generation_time: float = 150.0):  # 2.5 minutes default
        self.max_generation_time = max_generation_time
        self.active_generations = {}  # {doc_id: {'start_time': timestamp, 'timeout_thread': thread}}
        self.event_handlers = []  # List of event handler callbacks
        self.error_handlers = []  # List of error handler callbacks
        self.data_stream_handlers = []  # List of data stream handler callbacks
        
    def register_event_handler(self, handler: Callable):
        """Register an event handler callback"""
        self.event_handlers.append(handler)
        
    def register_error_handler(self, handler: Callable):
        """Register an error handler callback"""
        self.error_handlers.append(handler)
        
    def register_data_stream_handler(self, handler: Callable):
        """Register a data stream handler callback"""
        self.data_stream_handlers.append(handler)
        
    def trigger_event(self, doc_id: str, event_type: str, data: Dict[str, Any]):
        """Trigger an event to all registered handlers"""
        event_data = {
            'doc_id': doc_id,
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }
        
        for handler in self.event_handlers:
            try:
                handler(event_data)
            except Exception as e:
                print(f"[TimeoutHandler] Error in event handler: {e}", flush=True)
                
    def trigger_error(self, doc_id: str, error_type: str, error: Exception, context: Dict[str, Any] = None):
        """Trigger an error to all registered handlers"""
        error_data = {
            'doc_id': doc_id,
            'error_type': error_type,
            'error': str(error),
            'error_class': type(error).__name__,
            'timestamp': datetime.utcnow().isoformat(),
            'context': context or {}
        }
        
        for handler in self.error_handlers:
            try:
                handler(error_data)
            except Exception as e:
                print(f"[TimeoutHandler] Error in error handler: {e}", flush=True)
                
    def trigger_data_stream(self, doc_id: str, stream_type: str, data: Any, metadata: Dict[str, Any] = None):
        """Trigger a data stream event to all registered handlers"""
        stream_data = {
            'doc_id': doc_id,
            'stream_type': stream_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data,
            'metadata': metadata or {}
        }
        
        for handler in self.data_stream_handlers:
            try:
                handler(stream_data)
            except Exception as e:
                print(f"[TimeoutHandler] Error in data stream handler: {e}", flush=True)
        
    def start_generation(self, doc_id: str):
        """Start tracking generation time for a documentary"""
        start_time = time.time()
        
        def timeout_check():
            """Check for timeout"""
            while True:
                time.sleep(5)  # Check every 5 seconds
                
                if doc_id not in self.active_generations:
                    break
                    
                elapsed = time.time() - start_time
                remaining = self.max_generation_time - elapsed
                
                if elapsed >= self.max_generation_time:
                    # Timeout reached
                    self.trigger_error(
                        doc_id,
                        'timeout',
                        TimeoutError(f"Generation timeout after {elapsed:.1f} seconds"),
                        {'elapsed_time': elapsed, 'max_time': self.max_generation_time}
                    )
                    
                    # Trigger timeout event
                    self.trigger_event(
                        doc_id,
                        'timeout_reached',
                        {
                            'elapsed_time': elapsed,
                            'max_time': self.max_generation_time,
                            'action': 'abort_generation'
                        }
                    )
                    break
                elif remaining <= 30:  # Warn at 30 seconds remaining
                    self.trigger_event(
                        doc_id,
                        'timeout_warning',
                        {
                            'remaining_time': remaining,
                            'elapsed_time': elapsed,
                            'warning_level': 'critical' if remaining <= 10 else 'warning'
                        }
                    )
        
        timeout_thread = threading.Thread(target=timeout_check, daemon=True)
        timeout_thread.start()
        
        self.active_generations[doc_id] = {
            'start_time': start_time,
            'timeout_thread': timeout_thread
        }
        
        self.trigger_event(
            doc_id,
            'generation_started',
            {
                'max_time': self.max_generation_time,
                'start_timestamp': datetime.utcnow().isoformat()
            }
        )
        
        print(f"[TimeoutHandler] Started generation tracking for {doc_id} (max time: {self.max_generation_time}s)", flush=True)
        
    def stop_generation(self, doc_id: str, reason: str = 'completed'):
        """Stop tracking generation time for a documentary"""
        if doc_id not in self.active_generations:
            return
            
        gen_info = self.active_generations.pop(doc_id)
        elapsed = time.time() - gen_info['start_time']
        
        self.trigger_event(
            doc_id,
            'generation_stopped',
            {
                'reason': reason,
                'elapsed_time': elapsed,
                'max_time': self.max_generation_time,
                'completed_within_limit': elapsed < self.max_generation_time
            }
        )
        
        print(f"[TimeoutHandler] Stopped generation tracking for {doc_id} (reason: {reason}, elapsed: {elapsed:.1f}s)", flush=True)
        
    def get_elapsed_time(self, doc_id: str) -> Optional[float]:
        """Get elapsed time for a generation"""
        if doc_id not in self.active_generations:
            return None
        return time.time() - self.active_generations[doc_id]['start_time']
        
    def get_remaining_time(self, doc_id: str) -> Optional[float]:
        """Get remaining time for a generation"""
        elapsed = self.get_elapsed_time(doc_id)
        if elapsed is None:
            return None
        return max(0, self.max_generation_time - elapsed)


# Global instance
generator_timeout_handler = GeneratorTimeoutHandler(max_generation_time=150.0)  # 2.5 minutes
