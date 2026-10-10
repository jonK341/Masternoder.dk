"""
Production Debugger System
Comprehensive debugging and monitoring for all production systems
"""
import logging
import traceback
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict
import sys

logger = logging.getLogger(__name__)


class ProductionDebugger:
    """
    Comprehensive production debugger that monitors, logs, and fixes issues
    across all systems, routes, and frontend integrations.
    """
    
    def __init__(self):
        self.debug_log = []
        self.errors = []
        self.warnings = []
        self.fixes_applied = []
        self.system_status = {}
        self.route_status = {}
        self.frontend_status = {}
        self.url_test_results = {}
        
    def debug_system(self, system_name: str, system_instance: Any = None) -> Dict[str, Any]:
        """Debug a specific system"""
        result = {
            'system': system_name,
            'status': 'unknown',
            'errors': [],
            'warnings': [],
            'methods': [],
            'attributes': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            if system_instance is None:
                # Try to import the system
                try:
                    module_path = f"backend.services.{system_name}"
                    module = __import__(module_path, fromlist=[system_name])
                    system_instance = getattr(module, system_name, None)
                except Exception as e:
                    result['status'] = 'not_found'
                    result['errors'].append(f"Could not import: {str(e)}")
                    return result
            
            if system_instance is None:
                result['status'] = 'not_found'
                return result
            
            # Check system attributes
            result['attributes'] = [attr for attr in dir(system_instance) if not attr.startswith('_')]
            
            # Check system methods
            result['methods'] = [method for method in dir(system_instance) 
                               if callable(getattr(system_instance, method, None)) and not method.startswith('_')]
            
            # Test basic functionality
            try:
                if hasattr(system_instance, 'get_user_data'):
                    test_data = system_instance.get_user_data('test_user')
                    result['status'] = 'functional'
                elif hasattr(system_instance, 'get_data'):
                    test_data = system_instance.get_data('test_user')
                    result['status'] = 'functional'
                else:
                    result['status'] = 'available'
                    result['warnings'].append("No standard get method found")
            except Exception as e:
                result['status'] = 'error'
                result['errors'].append(f"Test failed: {str(e)}")
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Debug failed: {str(e)}")
            result['traceback'] = traceback.format_exc()
        
        self.system_status[system_name] = result
        return result
    
    def debug_route(self, route_path: str, blueprint_name: str = None) -> Dict[str, Any]:
        """Debug a specific route"""
        result = {
            'route': route_path,
            'blueprint': blueprint_name,
            'status': 'unknown',
            'errors': [],
            'warnings': [],
            'methods': ['GET'],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            from flask import current_app
            
            # Check if route exists in Flask app
            with current_app.app_context():
                url_map = current_app.url_map
                route_found = False
                
                for rule in url_map.iter_rules():
                    if route_path in str(rule) or (blueprint_name and blueprint_name in str(rule)):
                        route_found = True
                        result['methods'] = list(rule.methods)
                        result['endpoint'] = rule.endpoint
                        break
                
                if route_found:
                    result['status'] = 'registered'
                else:
                    result['status'] = 'not_found'
                    result['warnings'].append("Route not found in Flask URL map")
        
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Debug failed: {str(e)}")
            result['traceback'] = traceback.format_exc()
        
        self.route_status[route_path] = result
        return result
    
    def debug_frontend(self, page_path: str) -> Dict[str, Any]:
        """Debug a frontend page"""
        result = {
            'page': page_path,
            'status': 'unknown',
            'errors': [],
            'warnings': [],
            'api_calls': [],
            'static_files': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            full_path = f"/var/www/html/{page_path}"
            if not os.path.exists(full_path):
                result['status'] = 'not_found'
                return result
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract API calls
            import re
            api_patterns = [
                r'fetch\(["\']([^"\']+api[^"\']+)["\']',
                r'fetch\(`([^`]+api[^`]+)`',
                r'\.get\(["\']([^"\']+api[^"\']+)["\']',
                r'\.post\(["\']([^"\']+api[^"\']+)["\']',
            ]
            
            for pattern in api_patterns:
                matches = re.findall(pattern, content)
                result['api_calls'].extend(matches)
            
            # Extract static file references
            static_patterns = [
                r'src=["\']([^"\']+\.(js|css))["\']',
                r'href=["\']([^"\']+\.(js|css))["\']',
            ]
            
            for pattern in static_patterns:
                matches = re.findall(pattern, content)
                result['static_files'].extend([m[0] if isinstance(m, tuple) else m for m in matches])
            
            result['status'] = 'found'
            result['api_calls'] = list(set(result['api_calls']))
            result['static_files'] = list(set(result['static_files']))
            
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Debug failed: {str(e)}")
            result['traceback'] = traceback.format_exc()
        
        self.frontend_status[page_path] = result
        return result
    
    def test_url(self, url: str, method: str = 'GET') -> Dict[str, Any]:
        """Test a URL endpoint"""
        result = {
            'url': url,
            'method': method,
            'status': 'unknown',
            'status_code': None,
            'response_time': None,
            'errors': [],
            'warnings': [],
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            import requests
            import time
            
            start_time = time.time()
            response = requests.request(method, url, timeout=10, allow_redirects=False)
            response_time = time.time() - start_time
            
            result['status_code'] = response.status_code
            result['response_time'] = round(response_time * 1000, 2)  # ms
            result['content_type'] = response.headers.get('Content-Type', '')
            result['content_length'] = len(response.content)
            
            if response.status_code == 200:
                result['status'] = 'ok'
                # Try to parse JSON
                try:
                    result['json'] = response.json()
                except:
                    result['data'] = response.text[:500]  # First 500 chars
            elif response.status_code == 404:
                result['status'] = 'not_found'
                result['errors'].append(f"404 Not Found: {url}")
            elif response.status_code >= 500:
                result['status'] = 'server_error'
                result['errors'].append(f"{response.status_code} Server Error: {url}")
            else:
                result['status'] = 'error'
                result['warnings'].append(f"Status {response.status_code}: {url}")
        
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['errors'].append(f"Timeout: {url}")
        except requests.exceptions.ConnectionError:
            result['status'] = 'connection_error'
            result['errors'].append(f"Connection Error: {url}")
        except Exception as e:
            result['status'] = 'error'
            result['errors'].append(f"Test failed: {str(e)}")
            result['traceback'] = traceback.format_exc()
        
        self.url_test_results[url] = result
        return result
    
    def test_all_routes(self, base_url: str = 'https://masternoder.dk') -> Dict[str, Any]:
        """Test all registered routes"""
        results = {
            'total': 0,
            'ok': 0,
            'errors': 0,
            'not_found': 0,
            'server_errors': 0,
            'routes': []
        }
        
        try:
            from flask import current_app
            
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    route_path = str(rule)
                    # Skip static files and internal routes
                    if '/static/' in route_path or route_path.startswith('/_'):
                        continue
                    
                    # Build full URL
                    full_url = f"{base_url}{route_path}"
                    
                    # Test the route
                    test_result = self.test_url(full_url)
                    results['total'] += 1
                    
                    if test_result['status'] == 'ok':
                        results['ok'] += 1
                    elif test_result['status'] == 'not_found':
                        results['not_found'] += 1
                    elif test_result['status'] == 'server_error':
                        results['server_errors'] += 1
                    else:
                        results['errors'] += 1
                    
                    results['routes'].append(test_result)
        
        except Exception as e:
            logger.error(f"Error testing all routes: {e}")
            results['error'] = str(e)
        
        return results
    
    def find_broken_urls(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Find broken URLs from a list"""
        broken = []
        
        for url in urls:
            result = self.test_url(url)
            if result['status'] not in ['ok', 'unknown']:
                broken.append(result)
        
        return broken
    
    def check_duplicate_blueprints(self) -> Dict[str, Any]:
        """Check for duplicate blueprint registrations"""
        result = {
            'duplicates': [],
            'total_blueprints': 0,
            'unique_blueprints': 0,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            from flask import current_app
            
            with current_app.app_context():
                blueprint_names = {}
                for name, blueprint in current_app.blueprints.items():
                    if name in blueprint_names:
                        result['duplicates'].append({
                            'name': name,
                            'first': blueprint_names[name],
                            'second': str(blueprint)
                        })
                    else:
                        blueprint_names[name] = str(blueprint)
                
                result['total_blueprints'] = len(current_app.blueprints)
                result['unique_blueprints'] = len(blueprint_names)
        
        except Exception as e:
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
        
        return result
    
    def debug_all_systems(self) -> Dict[str, Any]:
        """Debug all systems"""
        results = {}
        
        # Get all service files
        services_dir = "/var/www/html/backend/services"
        if os.path.exists(services_dir):
            for filename in os.listdir(services_dir):
                if filename.endswith('.py') and not filename.startswith('_'):
                    system_name = filename[:-3]
                    results[system_name] = self.debug_system(system_name)
        
        return results
    
    def debug_all_routes(self) -> Dict[str, Any]:
        """Debug all routes"""
        results = {}
        
        try:
            from flask import current_app
            
            with current_app.app_context():
                for rule in current_app.url_map.iter_rules():
                    route_path = str(rule)
                    results[route_path] = self.debug_route(route_path, rule.endpoint)
        
        except Exception as e:
            logger.error(f"Error debugging routes: {e}")
        
        return results
    
    def fix_missing_imports(self, file_path: str) -> List[str]:
        """Fix missing imports in a file"""
        fixes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Common import fixes
            import_fixes = {
                'from src.db.models import': 'from backend.services.database_redesign import',
                'from src.services import': 'from backend.services import',
                'from src.utils import': 'from backend.utils import',
            }
            
            for old_import, new_import in import_fixes.items():
                if old_import in content and new_import not in content:
                    content = content.replace(old_import, new_import)
                    fixes.append(f"Fixed import: {old_import} -> {new_import}")
            
            if fixes:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixes_applied.extend(fixes)
        
        except Exception as e:
            logger.error(f"Error fixing imports in {file_path}: {e}")
        
        return fixes
    
    def fix_missing_routes(self, blueprint_file: str) -> List[str]:
        """Fix missing route decorators"""
        fixes = []
        
        try:
            with open(blueprint_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for common route patterns
            if '@' not in content and 'route(' in content:
                # Add Flask blueprint import if missing
                if 'from flask import Blueprint' not in content:
                    content = 'from flask import Blueprint, jsonify, request\n' + content
                    fixes.append("Added Flask imports")
            
            if fixes:
                with open(blueprint_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixes_applied.extend(fixes)
        
        except Exception as e:
            logger.error(f"Error fixing routes in {blueprint_file}: {e}")
        
        return fixes
    
    def generate_report(self) -> str:
        """Generate comprehensive debug report"""
        report = []
        report.append("=" * 80)
        report.append("PRODUCTION DEBUGGER REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        # System Status
        report.append("SYSTEM STATUS")
        report.append("-" * 80)
        for system, status in self.system_status.items():
            report.append(f"{system}: {status.get('status', 'unknown')}")
            if status.get('errors'):
                for error in status['errors']:
                    report.append(f"  ERROR: {error}")
            if status.get('warnings'):
                for warning in status['warnings']:
                    report.append(f"  WARNING: {warning}")
        report.append("")
        
        # Route Status
        report.append("ROUTE STATUS")
        report.append("-" * 80)
        for route, status in self.route_status.items():
            report.append(f"{route}: {status.get('status', 'unknown')}")
        report.append("")
        
        # Frontend Status
        report.append("FRONTEND STATUS")
        report.append("-" * 80)
        for page, status in self.frontend_status.items():
            report.append(f"{page}: {status.get('status', 'unknown')}")
            if status.get('api_calls'):
                report.append(f"  API Calls: {len(status['api_calls'])}")
        report.append("")
        
        # URL Test Results
        if self.url_test_results:
            report.append("URL TEST RESULTS")
            report.append("-" * 80)
            broken = [r for r in self.url_test_results.values() if r['status'] != 'ok']
            report.append(f"Total tested: {len(self.url_test_results)}")
            report.append(f"Broken: {len(broken)}")
            for result in broken[:20]:  # Show first 20 broken URLs
                report.append(f"  {result['url']}: {result['status']} ({result.get('status_code', 'N/A')})")
        report.append("")
        
        # Fixes Applied
        if self.fixes_applied:
            report.append("FIXES APPLIED")
            report.append("-" * 80)
            for fix in self.fixes_applied:
                report.append(f"  - {fix}")
            report.append("")
        
        report.append("=" * 80)
        
        return "\n".join(report)


# Global instance
production_debugger = ProductionDebugger()
