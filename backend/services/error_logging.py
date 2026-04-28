"""
Error Logging Service
Centralized error logging and tracking system
"""
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Optional, List
from flask import request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ErrorLogger:
    """Centralized error logging service"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.logs_dir = os.path.join(self.base_dir, 'logs', 'errors')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Error statistics
        self.stats_file = os.path.join(self.logs_dir, 'error_stats.json')
        self.stats = self._load_stats()
    
    def _load_stats(self) -> Dict:
        """Load error statistics"""
        if os.path.exists(self.stats_file):
            try:
                with open(self.stats_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'total_errors': 0,
            'errors_by_type': {},
            'errors_by_endpoint': {},
            'recent_errors': []
        }
    
    def _save_stats(self):
        """Save error statistics"""
        try:
            with open(self.stats_file, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            print(f"Error saving stats: {e}")
    
    def log_error(self, 
                  error: Exception,
                  error_type: str = 'unknown',
                  endpoint: Optional[str] = None,
                  user_id: Optional[str] = None,
                  additional_data: Optional[Dict] = None):
        """Log an error"""
        timestamp = datetime.now().isoformat()
        
        # Get request info if available
        request_info = {}
        try:
            if request:
                request_info = {
                    'path': request.path,
                    'method': request.method,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.headers.get('User-Agent', ''),
                }
        except:
            pass
        
        # Build error entry
        error_entry = {
            'timestamp': timestamp,
            'error_type': error_type,
            'error_message': str(error),
            'error_class': error.__class__.__name__,
            'endpoint': endpoint or request_info.get('path', 'unknown'),
            'user_id': user_id,
            'request_info': request_info,
            'traceback': traceback.format_exc(),
            'additional_data': additional_data or {}
        }
        
        # Save to daily log file
        log_file = os.path.join(self.logs_dir, f"errors_{datetime.now().strftime('%Y%m%d')}.json")
        
        errors = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
            except:
                pass
        
        errors.append(error_entry)
        
        # Keep only last 1000 errors per day
        if len(errors) > 1000:
            errors = errors[-1000:]
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2)
        except Exception as e:
            print(f"Error writing to log file: {e}")
        
        # Update statistics
        self.stats['total_errors'] += 1
        
        # Count by type
        if error_type not in self.stats['errors_by_type']:
            self.stats['errors_by_type'][error_type] = 0
        self.stats['errors_by_type'][error_type] += 1
        
        # Count by endpoint
        endpoint_key = endpoint or request_info.get('path', 'unknown')
        if endpoint_key not in self.stats['errors_by_endpoint']:
            self.stats['errors_by_endpoint'][endpoint_key] = 0
        self.stats['errors_by_endpoint'][endpoint_key] += 1
        
        # Add to recent errors (keep last 50)
        self.stats['recent_errors'].append({
            'timestamp': timestamp,
            'error_type': error_type,
            'endpoint': endpoint_key,
            'message': str(error)[:100]
        })
        if len(self.stats['recent_errors']) > 50:
            self.stats['recent_errors'] = self.stats['recent_errors'][-50:]
        
        self._save_stats()
        
        return error_entry
    
    def log_api_error(self,
                      status_code: int,
                      error_message: str,
                      endpoint: Optional[str] = None,
                      user_id: Optional[str] = None,
                      request_data: Optional[Dict] = None):
        """Log an API error"""
        error_type = f'api_error_{status_code}'
        
        error_entry = {
            'timestamp': datetime.now().isoformat(),
            'error_type': error_type,
            'status_code': status_code,
            'error_message': error_message,
            'endpoint': endpoint,
            'user_id': user_id,
            'request_data': request_data or {}
        }
        
        # Save to API errors log
        log_file = os.path.join(self.logs_dir, f"api_errors_{datetime.now().strftime('%Y%m%d')}.json")
        
        errors = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    errors = json.load(f)
            except:
                pass
        
        errors.append(error_entry)
        
        # Keep only last 500 API errors per day
        if len(errors) > 500:
            errors = errors[-500:]
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(errors, f, indent=2)
        except Exception as e:
            print(f"Error writing API error log: {e}")
        
        # Update stats
        self.stats['total_errors'] += 1
        if error_type not in self.stats['errors_by_type']:
            self.stats['errors_by_type'][error_type] = 0
        self.stats['errors_by_type'][error_type] += 1
        
        endpoint_key = endpoint or 'unknown'
        if endpoint_key not in self.stats['errors_by_endpoint']:
            self.stats['errors_by_endpoint'][endpoint_key] = 0
        self.stats['errors_by_endpoint'][endpoint_key] += 1
        
        self._save_stats()
        
        return error_entry
    
    def get_statistics(self) -> Dict:
        """Get error statistics"""
        return self.stats
    
    def get_recent_errors(self, limit: int = 20) -> List[Dict]:
        """Get recent errors"""
        return self.stats.get('recent_errors', [])[-limit:]
    
    def get_errors_by_type(self, error_type: str) -> int:
        """Get count of errors by type"""
        return self.stats.get('errors_by_type', {}).get(error_type, 0)
    
    def get_errors_by_endpoint(self, endpoint: str) -> int:
        """Get count of errors by endpoint"""
        return self.stats.get('errors_by_endpoint', {}).get(endpoint, 0)

# Global instance
error_logger = ErrorLogger()
