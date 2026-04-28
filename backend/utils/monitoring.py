"""
Monitoring and Alerting Utilities
Basic monitoring for system metrics and alerts
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict
import threading

_metrics = defaultdict(list)
_alerts = []
_lock = threading.Lock()


class SystemMonitor:
    """Basic system monitoring and alerting"""
    
    def __init__(self, log_dir: Optional[str] = None):
        if log_dir is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            log_dir = os.path.join(base_dir, 'logs', 'monitoring')
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
    
    def record_metric(self, metric_name: str, value: float, tags: Optional[Dict] = None):
        """Record a metric"""
        with _lock:
            _metrics[metric_name].append({
                'value': value,
                'timestamp': datetime.utcnow().isoformat(),
                'tags': tags or {}
            })
            # Keep only last 1000 entries per metric
            if len(_metrics[metric_name]) > 1000:
                _metrics[metric_name] = _metrics[metric_name][-1000:]
    
    def record_alert(self, level: str, message: str, component: str = 'system'):
        """Record an alert"""
        alert = {
            'level': level,  # info, warning, error, critical
            'message': message,
            'component': component,
            'timestamp': datetime.utcnow().isoformat()
        }
        with _lock:
            _alerts.append(alert)
            # Keep only last 100 alerts
            if len(_alerts) > 100:
                _alerts[:] = _alerts[-100:]
        
        # Log critical alerts
        if level in ['error', 'critical']:
            try:
                log_file = os.path.join(self.log_dir, f'alerts_{datetime.utcnow().strftime("%Y-%m-%d")}.log')
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(alert) + '\n')
            except:
                pass
    
    def get_metrics(self, metric_name: Optional[str] = None, hours: int = 24) -> Dict:
        """Get metrics for the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with _lock:
            if metric_name:
                metrics = {metric_name: _metrics.get(metric_name, [])}
            else:
                metrics = dict(_metrics)
            
            # Filter by time
            filtered = {}
            for name, values in metrics.items():
                filtered[name] = [
                    v for v in values
                    if datetime.fromisoformat(v['timestamp']) > cutoff
                ]
            return filtered
    
    def get_alerts(self, level: Optional[str] = None, hours: int = 24) -> List[Dict]:
        """Get alerts for the last N hours"""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        with _lock:
            alerts = _alerts.copy()
        
        filtered = [
            a for a in alerts
            if datetime.fromisoformat(a['timestamp']) > cutoff
            and (level is None or a['level'] == level)
        ]
        return filtered
    
    def get_summary(self) -> Dict:
        """Get monitoring summary"""
        metrics = self.get_metrics(hours=1)
        alerts = self.get_alerts(hours=1)
        
        return {
            'metrics_count': sum(len(v) for v in metrics.values()),
            'active_metrics': len(metrics),
            'alerts_count': len(alerts),
            'critical_alerts': len([a for a in alerts if a['level'] == 'critical']),
            'error_alerts': len([a for a in alerts if a['level'] == 'error']),
            'timestamp': datetime.utcnow().isoformat()
        }


# Global monitor instance
system_monitor = SystemMonitor()
