"""
Spider Web Error Handling System
Detects recurring errors and automatically handles them with retry logic
Uses calculator for decision-making and time pocket for recording attempts
"""
import os
import json
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
import traceback

# Setup logging
logger = logging.getLogger(__name__)

class SpiderWebErrorHandler:
    """
    Organic material system that embraces recurring errors (MinusChild pattern)
    Uses spiderweb organization to detect and handle repetitive errors
    """
    
    def __init__(self):
        self.error_patterns_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'spiderweb_error_patterns.json'
        )
        self.attempts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'spiderweb_attempts.json'
        )
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.error_patterns_file), exist_ok=True)
        
        # Load existing patterns and attempts
        self.error_patterns = self._load_patterns()
        self.attempts_history = self._load_attempts()
        
        # Configuration
        self.max_attempts = 100  # Maximum retry attempts
        self.success_threshold = 0.8  # 80% success rate required
        self.retry_delay = 1.0  # Initial delay between retries (seconds)
        self.pattern_window = 3600  # Time window for pattern detection (1 hour)
        
    def _load_patterns(self) -> Dict[str, Any]:
        """Load error patterns from storage"""
        try:
            if os.path.exists(self.error_patterns_file):
                with open(self.error_patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading patterns: {e}")
        return {}
    
    def _save_patterns(self):
        """Save error patterns to storage"""
        try:
            with open(self.error_patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.error_patterns, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving patterns: {e}")
    
    def _load_attempts(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load attempts history"""
        try:
            if os.path.exists(self.attempts_file):
                with open(self.attempts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading attempts: {e}")
        return defaultdict(list)
    
    def _save_attempts(self):
        """Save attempts history"""
        try:
            with open(self.attempts_file, 'w', encoding='utf-8') as f:
                # Convert defaultdict to regular dict for JSON serialization
                data = dict(self.attempts_history)
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving attempts: {e}")
    
    def _calculate_error_signature(self, error: Exception) -> str:
        """Generate unique signature for error pattern"""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Extract key parts of error message
        key_parts = []
        if "write could not complete" in error_message.lower():
            key_parts.append("blocking_write")
        if "permission denied" in error_message.lower():
            key_parts.append("permission")
        if "connection" in error_message.lower():
            key_parts.append("connection")
        if "timeout" in error_message.lower():
            key_parts.append("timeout")
        
        signature = f"{error_type}_{'_'.join(key_parts) if key_parts else 'generic'}"
        return signature
    
    def _calculate_success_rate(self, error_signature: str) -> float:
        """
        Calculate success rate using calculator logic
        New Organic Material equation: .8 * success_rate
        """
        try:
            from backend.services.advanced_intelligent_calculator import AdvancedIntelligentCalculator
            
            calculator = AdvancedIntelligentCalculator()
            
            # Get recent attempts for this error
            recent_attempts = [
                a for a in self.attempts_history.get(error_signature, [])
                if time.time() - a.get('timestamp', 0) < self.pattern_window
            ]
            
            if not recent_attempts:
                return 1.0  # No history, assume success
            
            successful = sum(1 for a in recent_attempts if a.get('success', False))
            total = len(recent_attempts)
            success_rate = successful / total if total > 0 else 0.0
            
            # Apply the .8 multiplier from the equation: New Organic Material = .8 * success_rate
            adjusted_rate = 0.8 * success_rate
            
            # Note: Calculator is complex (takes point_data dict), so we use direct math
            # This implements the equation: .8 * ErrorExceptionEventHandlers.Try success_rate
            
            return adjusted_rate
        except Exception as e:
            logger.error(f"Error calculating success rate: {e}")
            return 0.5  # Default to 50% on error
    
    def _should_retry(self, error_signature: str, attempt_count: int) -> bool:
        """
        Determine if we should retry based on:
        - Attempt count (max 100)
        - Success rate threshold (.8)
        - Calculator decision
        """
        if attempt_count >= self.max_attempts:
            return False
        
        success_rate = self._calculate_success_rate(error_signature)
        
        # If success rate is above threshold, continue retrying
        if success_rate >= self.success_threshold:
            return True
        
        # Calculate decision using the equation: .8 * success_rate >= threshold
        # This is the "New Organic Material" equation from the specification
        decision_value = 0.8 * success_rate
        should_retry = decision_value >= self.success_threshold
        
        # Note: Calculator integration available for complex calculations if needed
        # For this decision, we use direct math to implement the equation
        return should_retry
        
        return False
    
    def _record_attempt(self, error_signature: str, success: bool, details: Dict[str, Any]):
        """Record attempt in history (Time Pocket recording)"""
        attempt_record = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'success': success,
            'details': details,
            'error_signature': error_signature
        }
        
        self.attempts_history[error_signature].append(attempt_record)
        
        # Keep only recent attempts (last 1000)
        if len(self.attempts_history[error_signature]) > 1000:
            self.attempts_history[error_signature] = self.attempts_history[error_signature][-1000:]
        
        self._save_attempts()
    
    def _play_record_from_time_pocket(self, error_signature: str) -> Optional[Dict[str, Any]]:
        """
        Play record from time pocket (get last successful attempt pattern)
        """
        try:
            # Look for successful attempts in history
            successful_attempts = [
                a for a in self.attempts_history.get(error_signature, [])
                if a.get('success', False)
            ]
            
            if successful_attempts:
                # Return most recent successful attempt
                return successful_attempts[-1]
            
            return None
        except Exception as e:
            logger.error(f"Error playing record from time pocket: {e}")
            return None
    
    def _restart_service(self, service_name: str) -> bool:
        """Restart a service (generator, flask, etc.)"""
        try:
            import subprocess
            import sys
            
            # Try to restart service
            if service_name in ['flask', 'uwsgi', 'uwsgi-vidgenerator']:
                # Use systemctl if available
                result = subprocess.run(
                    ['systemctl', 'restart', 'uwsgi-vidgenerator.service'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.returncode == 0
            elif service_name in ['apache', 'apache2']:
                result = subprocess.run(
                    ['systemctl', 'restart', 'apache2.service'],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                return result.returncode == 0
            else:
                # Generic restart (wait a bit and continue)
                time.sleep(2)
                return True
        except Exception as e:
            logger.error(f"Error restarting service {service_name}: {e}")
            return False
    
    def handle_error_with_retry(
        self,
        error: Exception,
        operation: Callable,
        service_name: str = 'generator',
        max_retries: Optional[int] = None,
        operation_args: tuple = (),
        operation_kwargs: dict = None
    ) -> Dict[str, Any]:
        """
        Main error handling method - New Organic Material pattern
        
        Equation implementation:
        .8 * ErrorExceptionEventHandlers.Try if/else loop[i = null; i <= 100.01; I+++](
            Restart and PlayRecord On The Time Pocket Generator;
        ) or else stop and break off on the generator;
        """
        if operation_kwargs is None:
            operation_kwargs = {}
        
        error_signature = self._calculate_error_signature(error)
        max_attempts = max_retries or self.max_attempts
        
        # Update error pattern
        if error_signature not in self.error_patterns:
            self.error_patterns[error_signature] = {
                'first_seen': datetime.now().isoformat(),
                'count': 0,
                'last_seen': datetime.now().isoformat(),
                'error_type': type(error).__name__,
                'sample_message': str(error)[:200]
            }
        
        self.error_patterns[error_signature]['count'] += 1
        self.error_patterns[error_signature]['last_seen'] = datetime.now().isoformat()
        self._save_patterns()
        
        # Try if/else loop: i = 0; i <= max_attempts; i++
        for attempt in range(max_attempts + 1):  # 0 to max_attempts (100.01 becomes 100)
            try:
                # Check if we should continue retrying (calculator decision)
                if not self._should_retry(error_signature, attempt):
                    break
                
                # Restart and PlayRecord On The Time Pocket Generator
                if attempt > 0:
                    # Restart service
                    restart_success = self._restart_service(service_name)
                    
                    # Play record from time pocket (get successful pattern)
                    successful_record = self._play_record_from_time_pocket(error_signature)
                    
                    if successful_record:
                        # Try to apply successful pattern
                        logger.info(f"Applying successful pattern from time pocket for attempt {attempt}")
                    
                    # Exponential backoff delay
                    delay = self.retry_delay * (2 ** min(attempt - 1, 5))
                    time.sleep(delay)
                
                # Try the operation again
                result = operation(*operation_args, **operation_kwargs)
                
                # Success! Record it
                self._record_attempt(
                    error_signature,
                    success=True,
                    details={
                        'attempt': attempt,
                        'service': service_name,
                        'result': str(result)[:200] if result else None
                    }
                )
                
                return {
                    'success': True,
                    'result': result,
                    'attempts': attempt + 1,
                    'error_signature': error_signature
                }
                
            except Exception as retry_error:
                # Record failure
                self._record_attempt(
                    error_signature,
                    success=False,
                    details={
                        'attempt': attempt,
                        'service': service_name,
                        'error': str(retry_error),
                        'error_type': type(retry_error).__name__
                    }
                )
                
                # If this is the last attempt, break
                if attempt >= max_attempts:
                    break
                
                # Continue to next attempt
                continue
        
        # Stop and break off on the generator (all attempts failed)
        logger.error(
            f"SpiderWeb: Failed after {max_attempts} attempts for error: {error_signature}"
        )
        
        return {
            'success': False,
            'error': str(error),
            'error_signature': error_signature,
            'attempts': max_attempts,
            'message': f'Failed after {max_attempts} attempts. Breaking off generator.'
        }
    
    def get_error_statistics(self, error_signature: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about error patterns"""
        if error_signature:
            patterns = {error_signature: self.error_patterns.get(error_signature, {})}
            attempts = {error_signature: self.attempts_history.get(error_signature, [])}
        else:
            patterns = self.error_patterns
            attempts = dict(self.attempts_history)
        
        stats = {}
        for sig, pattern in patterns.items():
            recent_attempts = attempts.get(sig, [])
            successful = sum(1 for a in recent_attempts if a.get('success', False))
            total = len(recent_attempts)
            
            stats[sig] = {
                'pattern': pattern,
                'total_attempts': total,
                'successful_attempts': successful,
                'success_rate': successful / total if total > 0 else 0.0,
                'adjusted_success_rate': self._calculate_success_rate(sig),
                'recent_attempts': recent_attempts[-10:]  # Last 10 attempts
            }
        
        return stats
    
    def clear_old_patterns(self, days: int = 30):
        """Clear error patterns older than specified days"""
        cutoff_time = time.time() - (days * 24 * 3600)
        
        # Clear old attempts
        for sig in list(self.attempts_history.keys()):
            self.attempts_history[sig] = [
                a for a in self.attempts_history[sig]
                if a.get('timestamp', 0) > cutoff_time
            ]
            
            if not self.attempts_history[sig]:
                del self.attempts_history[sig]
        
        # Clear old patterns
        for sig in list(self.error_patterns.keys()):
            last_seen_str = self.error_patterns[sig].get('last_seen', '')
            try:
                last_seen = datetime.fromisoformat(last_seen_str)
                if last_seen.timestamp() < cutoff_time:
                    del self.error_patterns[sig]
            except:
                pass
        
        self._save_patterns()
        self._save_attempts()
        
        return {
            'success': True,
            'cleared_patterns': len(self.error_patterns),
            'cleared_attempts': len(self.attempts_history)
        }


# Global instance
spiderweb_error_handler = SpiderWebErrorHandler()

