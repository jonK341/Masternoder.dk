"""
Scaling Queue System - Distributed queue for 1.3 billion users
Message queue with priorities and batch processing
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from collections import deque
import threading
import queue
import uuid


class ScalingQueueSystem:
    """
    Priority-based queue system for massive scale
    Supports multiple queues with different priorities
    """
    
    def __init__(self, max_queue_size: int = 10000000):  # 10M items per queue
        self.queues = {
            'high': queue.PriorityQueue(maxsize=max_queue_size),
            'medium': queue.PriorityQueue(maxsize=max_queue_size),
            'low': queue.PriorityQueue(maxsize=max_queue_size)
        }
        self.stats = {
            'enqueued': 0,
            'dequeued': 0,
            'failed': 0,
            'processed': 0
        }
        self.lock = threading.Lock()
    
    def enqueue(self, item: Dict[str, Any], priority: str = 'medium',
               priority_value: int = 5) -> Dict[str, Any]:
        """
        Enqueue item with priority
        
        Args:
            item: Item to enqueue
            priority: 'high', 'medium', or 'low'
            priority_value: Numeric priority (higher = more important, inverted for queue)
        """
        if priority not in self.queues:
            priority = 'medium'
        
        queue_item = {
            'item_id': str(uuid.uuid4()),
            'item': item,
            'priority': priority,
            'priority_value': priority_value,
            'enqueued_at': datetime.utcnow().isoformat()
        }
        
        try:
            # Use negative priority for correct ordering (higher priority = dequeued first)
            self.queues[priority].put_nowait((-priority_value, queue_item))
            with self.lock:
                self.stats['enqueued'] += 1
            return {
                'success': True,
                'item_id': queue_item['item_id'],
                'priority': priority,
                'queued': True
            }
        except queue.Full:
            with self.lock:
                self.stats['failed'] += 1
            return {
                'success': False,
                'error': f'{priority} queue full',
                'item_id': queue_item['item_id']
            }
    
    def dequeue(self, priority: str = None, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Dequeue item (tries high, then medium, then low)"""
        priorities_to_try = [priority] if priority and priority in self.queues else ['high', 'medium', 'low']
        
        for prio in priorities_to_try:
            try:
                priority_val, queue_item = self.queues[prio].get(timeout=timeout / len(priorities_to_try))
                with self.lock:
                    self.stats['dequeued'] += 1
                queue_item['dequeued_at'] = datetime.utcnow().isoformat()
                return queue_item
            except queue.Empty:
                continue
        
        return None
    
    def batch_dequeue(self, batch_size: int = 100, priority: str = None) -> List[Dict[str, Any]]:
        """Dequeue multiple items in batch"""
        items = []
        for _ in range(batch_size):
            item = self.dequeue(priority, timeout=0.1)
            if item:
                items.append(item)
            else:
                break
        
        with self.lock:
            self.stats['processed'] += len(items)
        
        return items
    
    def get_queue_size(self, priority: str = None) -> Dict[str, Any]:
        """Get queue sizes"""
        if priority:
            return {
                priority: self.queues[priority].qsize()
            }
        else:
            return {
                'high': self.queues['high'].qsize(),
                'medium': self.queues['medium'].qsize(),
                'low': self.queues['low'].qsize(),
                'total': sum(q.qsize() for q in self.queues.values())
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics"""
        queue_sizes = self.get_queue_size()
        
        return {
            'enqueued': self.stats['enqueued'],
            'dequeued': self.stats['dequeued'],
            'processed': self.stats['processed'],
            'failed': self.stats['failed'],
            'queue_sizes': queue_sizes,
            'pending': queue_sizes.get('total', 0)
        }


# Global queue instances
calculation_queue = ScalingQueueSystem(max_queue_size=5000000)  # Calculator jobs
event_queue = ScalingQueueSystem(max_queue_size=10000000)  # Events
user_update_queue = ScalingQueueSystem(max_queue_size=2000000)  # User updates

