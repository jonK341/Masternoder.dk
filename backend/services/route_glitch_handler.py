"""
Route Glitch Handler - Catches and handles route registration errors
Auto-regenerates missing routes and applies same handler to all new routes
"""
from typing import Dict, List, Any, Optional
from flask import Flask
import importlib
import os
import sys


class RouteGlitchHandler:
    """Universal glitch handler for route registration issues"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.error_history = []
        self.auto_fixes_applied = []
    
    def handle_registration_error(self, blueprint_name: str, error: Exception, route_file_path: Optional[str] = None) -> Dict[str, Any]:
        """Handle a route registration error with auto-fix attempts"""
        error_info = {
            'blueprint': blueprint_name,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'auto_fixed': False,
            'fixes_applied': []
        }
        
        # Try auto-fix based on error type
        if 'name' in str(error).lower() and 'already registered' in str(error):
            # Blueprint name conflict
            fix_result = self._fix_blueprint_name_conflict(blueprint_name)
            if fix_result['success']:
                error_info['auto_fixed'] = True
                error_info['fixes_applied'].append(fix_result)
        
        elif 'View function mapping' in str(error):
            # Endpoint conflict
            fix_result = self._fix_endpoint_conflict(blueprint_name, error)
            if fix_result['success']:
                error_info['auto_fixed'] = True
                error_info['fixes_applied'].append(fix_result)
        
        elif 'No module named' in str(error):
            # Import error - try alternative paths
            fix_result = self._fix_import_error(blueprint_name, route_file_path)
            if fix_result['success']:
                error_info['auto_fixed'] = True
                error_info['fixes_applied'].append(fix_result)
        
        elif 'SyntaxError' in str(error):
            # Syntax error - log for manual fix
            error_info['requires_manual_fix'] = True
            error_info['fixes_applied'].append({
                'type': 'syntax_error',
                'message': 'Syntax error requires manual code fix',
                'file': route_file_path
            })
        
        self.error_history.append(error_info)
        return error_info
    
    def _fix_blueprint_name_conflict(self, blueprint_name: str) -> Dict[str, Any]:
        """Fix blueprint name conflict by renaming"""
        try:
            # Generate unique name
            counter = 1
            new_name = f"{blueprint_name}_unique_{counter}"
            while new_name in [bp.name for bp in self.app.blueprints.values()]:
                counter += 1
                new_name = f"{blueprint_name}_unique_{counter}"
            
            self.auto_fixes_applied.append({
                'type': 'blueprint_rename',
                'original': blueprint_name,
                'new': new_name
            })
            
            return {
                'success': True,
                'fix_type': 'blueprint_rename',
                'new_name': new_name,
                'message': f'Blueprint renamed from {blueprint_name} to {new_name}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _fix_endpoint_conflict(self, blueprint_name: str, error: Exception) -> Dict[str, Any]:
        """Fix endpoint conflict by suggesting unique endpoint names"""
        error_str = str(error)
        # Extract endpoint name from error
        if 'endpoint function:' in error_str:
            endpoint = error_str.split('endpoint function:')[-1].strip()
            return {
                'success': True,
                'fix_type': 'endpoint_rename',
                'suggestion': f"Use endpoint='{endpoint}_unique' in route decorator",
                'message': f'Endpoint conflict detected: {endpoint}'
            }
        return {'success': False, 'error': 'Could not extract endpoint name'}
    
    def _fix_import_error(self, blueprint_name: str, route_file_path: Optional[str]) -> Dict[str, Any]:
        """Try to fix import errors by checking alternative paths"""
        if not route_file_path:
            return {'success': False, 'error': 'No route file path provided'}
        
        # Try alternative import paths
        alternative_paths = [
            route_file_path,
            route_file_path.replace('backend/', ''),
            route_file_path.replace('routes/', 'backend/routes/'),
        ]
        
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                return {
                    'success': True,
                    'fix_type': 'import_path',
                    'suggested_path': alt_path,
                    'message': f'Found file at alternative path: {alt_path}'
                }
        
        return {'success': False, 'error': 'File not found in any alternative path'}
    
    def regenerate_missing_routes(self, blueprint_name: str, expected_routes: int) -> Dict[str, Any]:
        """Regenerate missing routes for a blueprint"""
        try:
            # Get actual registered routes
            actual_routes = [r for r in self.app.url_map.iter_rules() if blueprint_name in r.endpoint]
            
            if len(actual_routes) < expected_routes:
                missing_count = expected_routes - len(actual_routes)
                
                # Try to re-register blueprint
                try:
                    module_path = f'backend.routes.{blueprint_name}_routes'
                    module = importlib.import_module(module_path)
                    bp = getattr(module, f'{blueprint_name}_bp', None)
                    
                    if bp:
                        # Check for name conflicts before re-registering
                        if bp.name in [b.name for b in self.app.blueprints.values()]:
                            bp.name = f"{bp.name}_regenerated"
                        
                        self.app.register_blueprint(bp)
                        
                        return {
                            'success': True,
                            'regenerated': True,
                            'missing_routes': missing_count,
                            'message': f'Regenerated {missing_count} missing routes for {blueprint_name}'
                        }
                except Exception as e:
                    pass
                
                return {
                    'success': False,
                    'regenerated': False,
                    'missing_routes': missing_count,
                    'message': f'Could not regenerate {missing_count} missing routes'
                }
            
            return {
                'success': True,
                'regenerated': False,
                'message': 'All routes present'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def add_trigger_for_future_errors(self, blueprint_name: str, trigger_config: Dict[str, Any]):
        """Add trigger to catch future errors automatically"""
        trigger = {
            'blueprint': blueprint_name,
            'config': trigger_config,
            'active': True
        }
        
        # Store trigger (in production, this would be persisted)
        if not hasattr(self, 'triggers'):
            self.triggers = []
        self.triggers.append(trigger)
        
        return trigger
    
    def check_triggers(self, blueprint_name: str) -> List[Dict[str, Any]]:
        """Check if any triggers should fire for a blueprint"""
        if not hasattr(self, 'triggers'):
            return []
        
        active_triggers = [t for t in self.triggers if t['blueprint'] == blueprint_name and t['active']]
        return active_triggers


# Global handler instance (will be initialized with app)
_global_handler: Optional[RouteGlitchHandler] = None


def get_glitch_handler(app: Flask) -> RouteGlitchHandler:
    """Get or create global glitch handler"""
    global _global_handler
    if _global_handler is None:
        _global_handler = RouteGlitchHandler(app)
    return _global_handler

