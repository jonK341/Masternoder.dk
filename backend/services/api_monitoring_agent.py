"""
API Monitoring Agent
Automated agent skill for monitoring API structure and maintaining scanner tasks
"""
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

class APIMonitoringAgent:
    """Agent skill for monitoring API structure and maintaining scanner tasks"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.monitoring_dir = os.path.join(self.base_dir, 'logs', 'api_monitoring')
        os.makedirs(self.monitoring_dir, exist_ok=True)
        self.state_file = os.path.join(self.monitoring_dir, 'monitoring_state.json')
        self.load_state()
    
    def load_state(self):
        """Load monitoring state"""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    self.state = json.load(f)
            except:
                self.state = self._default_state()
        else:
            self.state = self._default_state()
    
    def _default_state(self) -> Dict:
        """Default monitoring state"""
        return {
            'last_scan': None,
            'last_generation': None,
            'scan_count': 0,
            'generation_count': 0,
            'alerts': [],
            'monitoring_enabled': True,
            'auto_generate_enabled': False,
            'scan_interval_hours': 24,
            'thresholds': {
                'missing_methods_warning': 10,
                'missing_methods_critical': 50,
                'unregistered_blueprints_warning': 1,
                'broken_endpoints_warning': 5
            }
        }
    
    def save_state(self):
        """Save monitoring state"""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(self.state, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving monitoring state: {e}")
    
    def should_scan(self) -> bool:
        """Check if it's time to scan"""
        if not self.state.get('monitoring_enabled', True):
            return False
        
        last_scan = self.state.get('last_scan')
        if not last_scan:
            return True
        
        try:
            last_scan_time = datetime.fromisoformat(last_scan)
            interval = timedelta(hours=self.state.get('scan_interval_hours', 24))
            return datetime.now() - last_scan_time >= interval
        except:
            return True
    
    def perform_scan(self) -> Dict:
        """Perform API structure scan"""
        try:
            from backend.services.api_scanner import APIScanner
            
            scanner = APIScanner(self.base_dir)
            report = scanner.get_report()
            
            # Update state
            self.state['last_scan'] = datetime.now().isoformat()
            self.state['scan_count'] = self.state.get('scan_count', 0) + 1
            self.save_state()
            
            # Check thresholds and generate alerts
            alerts = self._check_thresholds(report)
            if alerts:
                self.state['alerts'].extend(alerts)
                self.save_state()
            
            # Log scan
            self._log_scan(report, alerts)
            
            return {
                'success': True,
                'report': report,
                'alerts': alerts,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _check_thresholds(self, report: Dict) -> List[Dict]:
        """Check report against thresholds and generate alerts"""
        alerts = []
        thresholds = self.state.get('thresholds', {})
        summary = report.get('summary', {})
        
        missing_methods = summary.get('missing_methods', 0)
        warning_threshold = thresholds.get('missing_methods_warning', 10)
        critical_threshold = thresholds.get('missing_methods_critical', 50)
        
        if missing_methods >= critical_threshold:
            alerts.append({
                'level': 'critical',
                'type': 'missing_methods',
                'message': f'Critical: {missing_methods} missing methods detected (threshold: {critical_threshold})',
                'value': missing_methods,
                'threshold': critical_threshold,
                'timestamp': datetime.now().isoformat()
            })
        elif missing_methods >= warning_threshold:
            alerts.append({
                'level': 'warning',
                'type': 'missing_methods',
                'message': f'Warning: {missing_methods} missing methods detected (threshold: {warning_threshold})',
                'value': missing_methods,
                'threshold': warning_threshold,
                'timestamp': datetime.now().isoformat()
            })
        
        # Check for unregistered blueprints
        # This would require comparing scanned blueprints with registered ones
        # For now, we'll just log the scan results
        
        return alerts
    
    def _log_scan(self, report: Dict, alerts: List[Dict]):
        """Log scan results"""
        log_file = os.path.join(self.monitoring_dir, f"scan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            with open(log_file, 'w') as f:
                json.dump({
                    'report': report,
                    'alerts': alerts,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, default=str)
        except Exception as e:
            print(f"Error logging scan: {e}")
    
    def auto_generate_missing(self, dry_run: bool = True) -> Dict:
        """Auto-generate missing methods if enabled"""
        if not self.state.get('auto_generate_enabled', False):
            return {
                'success': False,
                'message': 'Auto-generation is disabled',
                'enabled': False
            }
        
        try:
            from backend.services.api_scanner import APIScanner
            
            scanner = APIScanner(self.base_dir)
            missing = scanner.find_missing_methods()
            
            if not missing:
                return {
                    'success': True,
                    'message': 'No missing methods to generate',
                    'generated': 0
                }
            
            # Only generate if below critical threshold
            thresholds = self.state.get('thresholds', {})
            critical_threshold = thresholds.get('missing_methods_critical', 50)
            
            if len(missing) >= critical_threshold:
                return {
                    'success': False,
                    'message': f'Too many missing methods ({len(missing)}). Manual review required.',
                    'missing_count': len(missing),
                    'threshold': critical_threshold
                }
            
            # Generate methods
            results = scanner.auto_generate_missing_methods()
            
            if not dry_run:
                self.state['last_generation'] = datetime.now().isoformat()
                self.state['generation_count'] = self.state.get('generation_count', 0) + 1
                self.save_state()
            
            return {
                'success': True,
                'dry_run': dry_run,
                'results': results,
                'generated': len(results.get('generated', [])),
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_status(self) -> Dict:
        """Get monitoring agent status"""
        return {
            'enabled': self.state.get('monitoring_enabled', True),
            'auto_generate_enabled': self.state.get('auto_generate_enabled', False),
            'last_scan': self.state.get('last_scan'),
            'last_generation': self.state.get('last_generation'),
            'scan_count': self.state.get('scan_count', 0),
            'generation_count': self.state.get('generation_count', 0),
            'alerts_count': len(self.state.get('alerts', [])),
            'recent_alerts': self.state.get('alerts', [])[-10:],  # Last 10 alerts
            'should_scan': self.should_scan(),
            'scan_interval_hours': self.state.get('scan_interval_hours', 24),
            'thresholds': self.state.get('thresholds', {})
        }
    
    def get_alerts(self, limit: int = 50) -> List[Dict]:
        """Get recent alerts"""
        alerts = self.state.get('alerts', [])
        return alerts[-limit:] if limit else alerts
    
    def clear_alerts(self):
        """Clear all alerts"""
        self.state['alerts'] = []
        self.save_state()
    
    def update_config(self, config: Dict):
        """Update monitoring configuration"""
        if 'monitoring_enabled' in config:
            self.state['monitoring_enabled'] = config['monitoring_enabled']
        if 'auto_generate_enabled' in config:
            self.state['auto_generate_enabled'] = config['auto_generate_enabled']
        if 'scan_interval_hours' in config:
            self.state['scan_interval_hours'] = config['scan_interval_hours']
        if 'thresholds' in config:
            self.state['thresholds'].update(config['thresholds'])
        
        self.save_state()
        return self.get_status()
    
    def run_monitoring_cycle(self) -> Dict:
        """Run a complete monitoring cycle"""
        if not self.should_scan():
            return {
                'success': True,
                'message': 'Not time to scan yet',
                'should_scan': False
            }
        
        # Perform scan
        scan_result = self.perform_scan()
        
        # Auto-generate if enabled and conditions met
        generation_result = None
        if self.state.get('auto_generate_enabled', False) and scan_result.get('success'):
            report = scan_result.get('report', {})
            summary = report.get('summary', {})
            missing_count = summary.get('missing_methods', 0)
            
            # Only auto-generate if below warning threshold
            warning_threshold = self.state.get('thresholds', {}).get('missing_methods_warning', 10)
            
            if 0 < missing_count < warning_threshold:
                generation_result = self.auto_generate_missing(dry_run=False)
        
        return {
            'success': True,
            'scan': scan_result,
            'generation': generation_result,
            'timestamp': datetime.now().isoformat()
        }

# Global instance
api_monitoring_agent = APIMonitoringAgent()
