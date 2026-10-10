"""
System metrics and monitoring utilities
Tracks application performance, resource usage, and system health
"""
import time
import platform
import os
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None


class SystemMetrics:
    """Collects and tracks system metrics"""
    
    def __init__(self):
        """Initialize metrics collector"""
        self.request_times = deque(maxlen=1000)  # Store last 1000 request times
        self.request_counts = defaultdict(int)  # Count requests per endpoint
        self.error_counts = defaultdict(int)  # Count errors per endpoint
        self.start_time = time.time()
    
    def record_request(self, endpoint: str, duration: float, status_code: int = 200):
        """Record a request metric"""
        self.request_times.append(duration)
        self.request_counts[endpoint] += 1
        
        if status_code >= 400:
            self.error_counts[endpoint] += 1
    
    def get_request_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        if not self.request_times:
            return {
                'total_requests': 0,
                'avg_response_time': 0,
                'min_response_time': 0,
                'max_response_time': 0,
                'p95_response_time': 0,
                'p99_response_time': 0
            }
        
        sorted_times = sorted(self.request_times)
        total = len(sorted_times)
        
        return {
            'total_requests': total,
            'avg_response_time': sum(sorted_times) / total,
            'min_response_time': min(sorted_times),
            'max_response_time': max(sorted_times),
            'p95_response_time': sorted_times[int(total * 0.95)] if total > 0 else 0,
            'p99_response_time': sorted_times[int(total * 0.99)] if total > 0 else 0
        }
    
    def get_endpoint_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics per endpoint"""
        stats = {}
        for endpoint, count in self.request_counts.items():
            stats[endpoint] = {
                'request_count': count,
                'error_count': self.error_counts.get(endpoint, 0),
                'error_rate': (self.error_counts.get(endpoint, 0) / count * 100) if count > 0 else 0
            }
        return stats
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information"""
        info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'uptime_seconds': time.time() - self.start_time,
            'uptime_formatted': str(timedelta(seconds=int(time.time() - self.start_time)))
        }
        
        if PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(os.getpid())
                info['cpu_percent'] = process.cpu_percent(interval=0.1)
                info['memory_mb'] = process.memory_info().rss / 1024 / 1024
                info['memory_percent'] = process.memory_percent()
                
                # System-wide stats
                info['system_cpu_percent'] = psutil.cpu_percent(interval=0.1)
                info['system_memory'] = {
                    'total_mb': psutil.virtual_memory().total / 1024 / 1024,
                    'available_mb': psutil.virtual_memory().available / 1024 / 1024,
                    'percent_used': psutil.virtual_memory().percent
                }
                
                # Disk usage
                disk = psutil.disk_usage('/')
                info['disk'] = {
                    'total_gb': disk.total / 1024 / 1024 / 1024,
                    'used_gb': disk.used / 1024 / 1024 / 1024,
                    'free_gb': disk.free / 1024 / 1024 / 1024,
                    'percent_used': disk.percent
                }
            except Exception:
                info['psutil_error'] = 'Could not collect system stats'
        else:
            info['psutil_available'] = False
        
        return info
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        request_stats = self.get_request_stats()
        system_info = self.get_system_info()
        
        # Determine health status
        health = 'healthy'
        issues = []
        
        # Check response times
        if request_stats['avg_response_time'] > 1.0:  # > 1 second average
            issues.append('High average response time')
            health = 'degraded'
        
        # Check error rate
        total_errors = sum(self.error_counts.values())
        total_requests = sum(self.request_counts.values())
        if total_requests > 0:
            error_rate = (total_errors / total_requests) * 100
            if error_rate > 5:  # > 5% error rate
                issues.append(f'High error rate: {error_rate:.1f}%')
                health = 'unhealthy'
        
        # Check system resources (if available)
        if PSUTIL_AVAILABLE and 'memory_percent' in system_info:
            if system_info.get('memory_percent', 0) > 90:
                issues.append('High memory usage')
                health = 'degraded'
            
            if system_info.get('system_memory', {}).get('percent_used', 0) > 95:
                issues.append('System memory critically high')
                health = 'unhealthy'
        
        return {
            'status': health,
            'uptime_seconds': system_info.get('uptime_seconds', 0),
            'uptime_formatted': system_info.get('uptime_formatted', ''),
            'request_stats': request_stats,
            'issues': issues,
            'timestamp': datetime.utcnow().isoformat()
        }


# Global metrics instance
_system_metrics = SystemMetrics()


def get_system_metrics() -> SystemMetrics:
    """Get global system metrics instance"""
    return _system_metrics

