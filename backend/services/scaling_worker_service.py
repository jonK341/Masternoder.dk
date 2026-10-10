"""
Scaling Worker Service - Background workers for processing queues
Processes calculation queue and event queue for 1.3 billion users
"""
from typing import Dict, Any
import threading
import time

try:
    from backend.services.scaling_calculator_distributed import scaling_calculator_distributed
    from backend.services.scaling_queue_system import calculation_queue, event_queue
    from backend.services.scaling_event_system import scaling_event_system
    CALCULATOR_AVAILABLE = True
except ImportError:
    scaling_calculator_distributed = None
    calculation_queue = None
    event_queue = None
    scaling_event_system = None
    CALCULATOR_AVAILABLE = False


class ScalingWorkerService:
    """
    Worker service for processing queues
    Runs background threads to process calculations and events
    """
    
    def __init__(self):
        self.workers = []
        self.running = False
        self.worker_count = 0
    
    def calculation_worker(self, worker_id: int):
        """Worker thread for processing calculation queue"""
        print(f"[ScalingWorker] Calculation worker {worker_id} started", flush=True)
        
        while self.running:
            try:
                if not calculation_queue:
                    time.sleep(1)
                    continue
                
                # Get calculation from queue
                calculation_item = calculation_queue.dequeue(priority=None, timeout=1.0)
                
                if calculation_item:
                    if scaling_calculator_distributed:
                        result = scaling_calculator_distributed.process_queued_calculation(
                            calculation_item.get('item', {})
                        )
                        if result.get('success'):
                            print(f"[ScalingWorker] Calculation {calculation_item.get('item', {}).get('calculation_id', 'unknown')} completed", flush=True)
                        else:
                            print(f"[ScalingWorker] Calculation failed: {result.get('error')}", flush=True)
            except Exception as e:
                print(f"[ScalingWorker] Calculation worker {worker_id} error: {e}", flush=True)
                time.sleep(1)
    
    def event_worker(self, worker_id: int):
        """Worker thread for processing event queue"""
        print(f"[ScalingWorker] Event worker {worker_id} started", flush=True)
        
        while self.running:
            try:
                if not event_queue or not scaling_event_system:
                    time.sleep(1)
                    continue
                
                # Get event from queue
                event_item = event_queue.dequeue(priority=None, timeout=1.0)
                
                if event_item:
                    event = event_item.get('item', {})
                    scaling_event_system.process_event(event)
            except Exception as e:
                print(f"[ScalingWorker] Event worker {worker_id} error: {e}", flush=True)
                time.sleep(1)
    
    def start_workers(self, calculation_workers: int = 20, event_workers: int = 10):
        """Start worker threads"""
        if self.running:
            return {'success': False, 'error': 'Workers already running'}
        
        self.running = True
        
        # Start calculation workers
        for i in range(calculation_workers):
            thread = threading.Thread(target=self.calculation_worker, args=(i,), daemon=True)
            thread.start()
            self.workers.append(thread)
            self.worker_count += 1
        
        # Start event workers
        for i in range(event_workers):
            thread = threading.Thread(target=self.event_worker, args=(i,), daemon=True)
            thread.start()
            self.workers.append(thread)
            self.worker_count += 1
        
        return {
            'success': True,
            'calculation_workers': calculation_workers,
            'event_workers': event_workers,
            'total_workers': self.worker_count
        }
    
    def stop_workers(self):
        """Stop all worker threads"""
        self.running = False
        
        # Wait for threads to finish
        for thread in self.workers:
            thread.join(timeout=5)
        
        self.workers.clear()
        self.worker_count = 0
        
        return {'success': True, 'workers_stopped': len(self.workers)}


# Global instance
scaling_worker_service = ScalingWorkerService()

