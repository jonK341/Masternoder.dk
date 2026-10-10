"""
Scaling Calculator Distributed - Distributed calculator for 1.3 billion users
Uses queues, caching, and event system for massive scale
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

try:
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    from backend.services.scaling_cache_system import calculation_cache, user_cache
    from backend.services.scaling_queue_system import calculation_queue
    from backend.services.scaling_event_system import scaling_event_system
    CALCULATOR_AVAILABLE = True
except ImportError:
    advanced_intelligent_calculator = None
    calculation_cache = None
    calculation_queue = None
    scaling_event_system = None
    CALCULATOR_AVAILABLE = False


class ScalingCalculatorDistributed:
    """
    Distributed calculator system for 1.3 billion users
    Uses caching, queuing, and event-driven architecture
    """
    
    def __init__(self):
        self.active_calculations = {}  # {calculation_id: calculation_data}
        self.calculation_results = {}  # {calculation_id: result}
        self.stats = {
            'total_calculations': 0,
            'cached_calculations': 0,
            'queued_calculations': 0,
            'completed_calculations': 0,
            'failed_calculations': 0
        }
    
    def calculate_async(self, user_id: str, point_data: Dict[str, Any],
                       priority: str = 'medium', use_cache: bool = True) -> Dict[str, Any]:
        """
        Calculate asynchronously using queue system
        
        Args:
            user_id: User identifier
            point_data: Point data for calculation
            priority: Queue priority ('high', 'medium', 'low')
            use_cache: Whether to check cache first
        """
        # Generate cache key
        cache_key = f"calc_{user_id}_{hash(str(point_data))}"
        
        # Check cache first
        if use_cache and calculation_cache:
            cached_result = calculation_cache.get(cache_key)
            if cached_result:
                self.stats['cached_calculations'] += 1
                return {
                    'success': True,
                    'calculation_id': cached_result.get('calculation_id'),
                    'result': cached_result.get('result'),
                    'cached': True
                }
        
        # Queue calculation
        calculation_id = str(uuid.uuid4())
        calculation_item = {
            'calculation_id': calculation_id,
            'user_id': user_id,
            'point_data': point_data,
            'cache_key': cache_key,
            'created_at': datetime.utcnow().isoformat()
        }
        
        queue_result = calculation_queue.enqueue(calculation_item, priority=priority)
        
        if queue_result.get('success'):
            self.active_calculations[calculation_id] = calculation_item
            self.stats['queued_calculations'] += 1
            
            # Emit calculation event
            if scaling_event_system:
                scaling_event_system.emit('calculation_queued', {
                    'calculation_id': calculation_id,
                    'user_id': user_id
                }, user_id=user_id, priority=8 if priority == 'high' else 5)
            
            return {
                'success': True,
                'calculation_id': calculation_id,
                'queued': True,
                'priority': priority
            }
        else:
            self.stats['failed_calculations'] += 1
            return {
                'success': False,
                'error': 'Queue full',
                'calculation_id': calculation_id
            }
    
    def calculate_sync(self, user_id: str, point_data: Dict[str, Any],
                      use_cache: bool = True) -> Dict[str, Any]:
        """
        Calculate synchronously (for immediate results)
        
        Args:
            user_id: User identifier
            point_data: Point data for calculation
            use_cache: Whether to check cache first
        """
        if not CALCULATOR_AVAILABLE:
            return {'success': False, 'error': 'Calculator not available'}
        
        # Generate cache key
        cache_key = f"calc_{user_id}_{hash(str(point_data))}"
        
        # Check cache first
        if use_cache and calculation_cache:
            cached_result = calculation_cache.get(cache_key)
            if cached_result:
                self.stats['cached_calculations'] += 1
                return {
                    'success': True,
                    'calculation_id': cached_result.get('calculation_id'),
                    'result': cached_result.get('result'),
                    'cached': True
                }
        
        # Perform calculation
        try:
            calculation_id = str(uuid.uuid4())
            result = advanced_intelligent_calculator.calculate_with_intelligence(
                point_data, user_id
            )
            
            # Cache result
            if calculation_cache:
                calculation_cache.set(cache_key, {
                    'calculation_id': calculation_id,
                    'result': result,
                    'user_id': user_id
                }, ttl=300)  # Cache for 5 minutes
            
            self.stats['total_calculations'] += 1
            self.stats['completed_calculations'] += 1
            
            # Emit calculation event
            if scaling_event_system:
                scaling_event_system.emit('calculation_completed', {
                    'calculation_id': calculation_id,
                    'user_id': user_id,
                    'result': result
                }, user_id=user_id, priority=5)
            
            return {
                'success': True,
                'calculation_id': calculation_id,
                'result': result,
                'cached': False
            }
        except Exception as e:
            self.stats['failed_calculations'] += 1
            return {
                'success': False,
                'error': str(e)
            }
    
    def process_queued_calculation(self, calculation_item: Dict[str, Any]) -> Dict[str, Any]:
        """Process a queued calculation (called by worker)"""
        calculation_id = calculation_item.get('calculation_id')
        user_id = calculation_item.get('user_id')
        point_data = calculation_item.get('point_data')
        cache_key = calculation_item.get('cache_key')
        
        if not CALCULATOR_AVAILABLE:
            return {'success': False, 'error': 'Calculator not available'}
        
        try:
            # Perform calculation
            result = advanced_intelligent_calculator.calculate_with_intelligence(
                point_data, user_id
            )
            
            # Cache result
            if calculation_cache:
                calculation_cache.set(cache_key, {
                    'calculation_id': calculation_id,
                    'result': result,
                    'user_id': user_id
                }, ttl=300)
            
            self.calculation_results[calculation_id] = result
            if calculation_id in self.active_calculations:
                del self.active_calculations[calculation_id]
            
            self.stats['total_calculations'] += 1
            self.stats['completed_calculations'] += 1
            
            # Emit completion event
            if scaling_event_system:
                scaling_event_system.emit('calculation_completed', {
                    'calculation_id': calculation_id,
                    'user_id': user_id,
                    'result': result
                }, user_id=user_id, priority=5)
            
            return {
                'success': True,
                'calculation_id': calculation_id,
                'result': result
            }
        except Exception as e:
            self.stats['failed_calculations'] += 1
            return {
                'success': False,
                'error': str(e),
                'calculation_id': calculation_id
            }
    
    def get_calculation_result(self, calculation_id: str) -> Dict[str, Any]:
        """Get result of a calculation"""
        if calculation_id in self.calculation_results:
            return {
                'success': True,
                'calculation_id': calculation_id,
                'result': self.calculation_results[calculation_id]
            }
        elif calculation_id in self.active_calculations:
            return {
                'success': False,
                'status': 'processing',
                'calculation_id': calculation_id
            }
        else:
            return {
                'success': False,
                'error': 'Calculation not found',
                'calculation_id': calculation_id
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get calculator statistics"""
        queue_stats = calculation_queue.get_stats() if calculation_queue else {}
        cache_stats = calculation_cache.get_stats() if calculation_cache else {}
        
        return {
            'total_calculations': self.stats['total_calculations'],
            'cached_calculations': self.stats['cached_calculations'],
            'queued_calculations': self.stats['queued_calculations'],
            'completed_calculations': self.stats['completed_calculations'],
            'failed_calculations': self.stats['failed_calculations'],
            'active_calculations': len(self.active_calculations),
            'cache_hit_rate': cache_stats.get('hit_rate', 0),
            'queue_size': queue_stats.get('pending', 0),
            'calculator_available': CALCULATOR_AVAILABLE
        }


# Global instance
scaling_calculator_distributed = ScalingCalculatorDistributed()

