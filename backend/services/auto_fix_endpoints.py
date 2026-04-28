"""
Auto-Fix Endpoints Service
Automatically creates missing endpoints when 404 errors occur
"""
import os
import json
import re
from datetime import datetime
from typing import Dict, Optional, List
from flask import request, jsonify

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AutoFixEndpoints:
    """Service to automatically fix missing endpoints"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.logs_dir = os.path.join(self.base_dir, 'logs', 'auto_fix_endpoints')
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Track fixed endpoints
        self.fixed_endpoints_file = os.path.join(self.logs_dir, 'fixed_endpoints.json')
        self.fixed_endpoints = self._load_fixed_endpoints()
        
        # Track 404 patterns
        self.patterns_file = os.path.join(self.logs_dir, '404_patterns.json')
        self.patterns = self._load_patterns()
    
    def _load_fixed_endpoints(self) -> Dict:
        """Load list of auto-fixed endpoints"""
        if os.path.exists(self.fixed_endpoints_file):
            try:
                with open(self.fixed_endpoints_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def _save_fixed_endpoints(self):
        """Save fixed endpoints list"""
        try:
            with open(self.fixed_endpoints_file, 'w', encoding='utf-8') as f:
                json.dump(self.fixed_endpoints, f, indent=2)
        except Exception as e:
            print(f"Error saving fixed endpoints: {e}")
    
    def _load_patterns(self) -> Dict:
        """Load 404 patterns for analysis"""
        if os.path.exists(self.patterns_file):
            try:
                with open(self.patterns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {'patterns': {}, 'counts': {}}
    
    def _save_patterns(self):
        """Save 404 patterns"""
        try:
            with open(self.patterns_file, 'w', encoding='utf-8') as f:
                json.dump(self.patterns, f, indent=2)
        except Exception as e:
            print(f"Error saving patterns: {e}")
    
    def log_404(self, path: str, method: str = 'GET'):
        """Log a 404 error for analysis"""
        # Extract pattern from path
        pattern = self._extract_pattern(path)
        
        if pattern not in self.patterns.get('patterns', {}):
            self.patterns.setdefault('patterns', {})[pattern] = {
                'original_path': path,
                'method': method,
                'first_seen': datetime.now().isoformat(),
                'count': 0,
                'examples': []
            }
        
        self.patterns['patterns'][pattern]['count'] += 1
        self.patterns['patterns'][pattern]['last_seen'] = datetime.now().isoformat()
        
        # Keep up to 5 examples
        if path not in self.patterns['patterns'][pattern]['examples']:
            if len(self.patterns['patterns'][pattern]['examples']) < 5:
                self.patterns['patterns'][pattern]['examples'].append(path)
        
        # Update counts
        if path not in self.patterns.get('counts', {}):
            self.patterns.setdefault('counts', {})[path] = 0
        self.patterns['counts'][path] += 1
        
        self._save_patterns()
    
    def _extract_pattern(self, path: str) -> str:
        """Extract pattern from path (replace IDs with placeholders)"""
        # Replace UUIDs
        pattern = re.sub(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '<uuid>', path, flags=re.IGNORECASE)
        
        # Replace numeric IDs
        pattern = re.sub(r'/\d+', '/<id>', pattern)
        
        # Replace user_id values
        pattern = re.sub(r'user_id=[^&]+', 'user_id=<user_id>', pattern)
        
        # Replace other common query params
        pattern = re.sub(r'[?&][^=]+=[^&]+', '', pattern)
        
        return pattern
    
    def should_auto_fix(self, path: str, method: str = 'GET') -> bool:
        """Determine if endpoint should be auto-fixed"""
        # Check if already fixed
        if path in self.fixed_endpoints:
            return False
        
        # Check pattern frequency
        pattern = self._extract_pattern(path)
        pattern_data = self.patterns.get('patterns', {}).get(pattern, {})
        
        # Auto-fix if seen 3+ times
        if pattern_data.get('count', 0) >= 3:
            return True
        
        # Auto-fix common API patterns
        if any(prefix in path for prefix in ['/api/', '/vidgenerator/api/']):
            return True
        
        return False
    
    def create_endpoint_response(self, path: str, method: str = 'GET') -> Dict:
        """Create a response for a missing endpoint"""
        # Extract endpoint info
        endpoint_info = self._analyze_endpoint(path, method)
        
        # Generate response based on endpoint type
        response = {
            'success': True,
            'message': 'Endpoint auto-created',
            'endpoint': path,
            'method': method,
            'auto_fixed': True,
            'timestamp': datetime.now().isoformat()
        }
        
        # Add data based on endpoint type
        if '/stats' in path:
            response['stats'] = {}
        elif '/points' in path:
            response['points'] = {}
            response['all_points'] = {}
        elif '/achievements' in path:
            response['achievements'] = []
        elif '/profile' in path:
            response['profile'] = {}
        elif '/battle' in path:
            response['battle_stats'] = {}
        elif '/game' in path:
            response['game_data'] = {}
        else:
            response['data'] = {}
        
        # Extract user_id if present
        user_id = request.args.get('user_id') or 'default_user'
        if '<user_id>' in path or 'user_id=' in path:
            response['user_id'] = user_id
        
        return response
    
    def _analyze_endpoint(self, path: str, method: str) -> Dict:
        """Analyze endpoint to determine what it should return"""
        info = {
            'type': 'generic',
            'category': 'unknown',
            'has_user_id': 'user_id' in path or 'user_id=' in request.query_string.decode() if request.query_string else False
        }
        
        # Categorize endpoint
        if '/stats' in path:
            info['type'] = 'stats'
            info['category'] = 'statistics'
        elif '/points' in path:
            info['type'] = 'points'
            info['category'] = 'points'
        elif '/profile' in path:
            info['type'] = 'profile'
            info['category'] = 'user_profile'
        elif '/battle' in path:
            info['type'] = 'battle'
            info['category'] = 'battle'
        elif '/game' in path:
            info['type'] = 'game'
            info['category'] = 'game'
        elif '/achievements' in path:
            info['type'] = 'achievements'
            info['category'] = 'achievements'
        
        return info
    
    def auto_fix_endpoint(self, path: str, method: str = 'GET') -> tuple:
        """Auto-fix an endpoint and return response"""
        # Log the 404
        self.log_404(path, method)
        
        # Check if should auto-fix
        if not self.should_auto_fix(path, method):
            return None, None
        
        # Create response
        response_data = self.create_endpoint_response(path, method)
        
        # Mark as fixed
        self.fixed_endpoints[path] = {
            'method': method,
            'fixed_at': datetime.now().isoformat(),
            'response_type': response_data.get('type', 'generic')
        }
        self._save_fixed_endpoints()
        
        # Log the fix
        self._log_fix(path, method, response_data)
        
        return response_data, 200
    
    def _log_fix(self, path: str, method: str, response: Dict):
        """Log an auto-fix"""
        log_entry = {
            'path': path,
            'method': method,
            'fixed_at': datetime.now().isoformat(),
            'response': response
        }
        
        log_file = os.path.join(self.logs_dir, f"fixes_{datetime.now().strftime('%Y%m%d')}.json")
        
        fixes = []
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    fixes = json.load(f)
            except:
                pass
        
        fixes.append(log_entry)
        
        try:
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(fixes, f, indent=2)
        except Exception as e:
            print(f"Error logging fix: {e}")
    
    def get_fixed_endpoints(self) -> Dict:
        """Get list of all auto-fixed endpoints"""
        return self.fixed_endpoints
    
    def get_404_patterns(self) -> Dict:
        """Get 404 patterns for analysis"""
        return self.patterns
    
    def get_statistics(self) -> Dict:
        """Get statistics about auto-fixes"""
        return {
            'total_fixed': len(self.fixed_endpoints),
            'total_patterns': len(self.patterns.get('patterns', {})),
            'total_404s': sum(self.patterns.get('counts', {}).values()),
            'recent_fixes': list(self.fixed_endpoints.items())[-10:]
        }

# Global instance
auto_fix_endpoints = AutoFixEndpoints()
