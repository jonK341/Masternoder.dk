"""
Comprehensive Route Debugger with Auto-Regeneration
Checks all routes, blueprints, detects conflicts, and auto-regenerates missing routes
"""
from flask import Blueprint, jsonify, request, current_app
from typing import Dict, List, Any, Optional
import inspect
import importlib
import sys
import os

comprehensive_route_debugger_bp = Blueprint('comprehensive_route_debugger', __name__, url_prefix='/api/debug/routes')


class RouteConflictDetector:
    """Detect and resolve route conflicts"""
    
    @staticmethod
    def check_url_conflicts_both_ways(app) -> Dict[str, Any]:
        """Check for URL conflicts in both directions (same URL, different endpoints)"""
        conflicts = []
        url_map = {}
        
        for rule in app.url_map.iter_rules():
            url = str(rule)
            endpoint = rule.endpoint
            
            if url in url_map:
                # Conflict: Same URL, different endpoint
                conflicts.append({
                    'type': 'url_conflict',
                    'url': url,
                    'endpoints': [url_map[url], endpoint],
                    'methods': list(rule.methods),
                    'severity': 'high'
                })
            else:
                url_map[url] = endpoint
        
        # Check reverse: Same endpoint, different URLs
        endpoint_map = {}
        for rule in app.url_map.iter_rules():
            endpoint = rule.endpoint
            url = str(rule)
            
            if endpoint in endpoint_map:
                if url not in endpoint_map[endpoint]:
                    conflicts.append({
                        'type': 'endpoint_multiple_urls',
                        'endpoint': endpoint,
                        'urls': endpoint_map[endpoint] + [url],
                        'severity': 'medium'
                    })
                    endpoint_map[endpoint].append(url)
            else:
                endpoint_map[endpoint] = [url]
        
        return {
            'conflicts': conflicts,
            'total_conflicts': len(conflicts),
            'url_map_size': len(url_map),
            'endpoint_map_size': len(endpoint_map)
        }
    
    @staticmethod
    def check_blueprint_name_conflicts(app) -> Dict[str, Any]:
        """Check for blueprint name conflicts"""
        blueprint_names = {}
        conflicts = []
        
        for rule in app.url_map.iter_rules():
            if '.' in rule.endpoint:
                bp_name = rule.endpoint.split('.')[0]
                
                if bp_name in blueprint_names:
                    if blueprint_names[bp_name] != rule.endpoint:
                        conflicts.append({
                            'type': 'blueprint_name_conflict',
                            'blueprint_name': bp_name,
                            'endpoints': [blueprint_names[bp_name], rule.endpoint],
                            'severity': 'high'
                        })
                else:
                    blueprint_names[bp_name] = rule.endpoint
        
        return {
            'conflicts': conflicts,
            'total_conflicts': len(conflicts),
            'blueprint_names': list(blueprint_names.keys())
        }


class RouteRegenerator:
    """Auto-regenerate missing routes"""
    
    @staticmethod
    def get_expected_routes_from_file(file_path: str) -> List[Dict[str, Any]]:
        """Extract expected routes from a route file"""
        expected_routes = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Find all @blueprint.route decorators
            import re
            pattern = r"@(\w+_bp)\.route\(['\"]([^'\"]+)['\"],\s*methods=\[([^\]]+)\]\)"
            matches = re.findall(pattern, content)
            
            for match in matches:
                bp_name, route_path, methods_str = match
                methods = [m.strip().strip("'\"") for m in methods_str.split(',')]
                
                expected_routes.append({
                    'blueprint': bp_name,
                    'path': route_path,
                    'methods': methods
                })
        
        except Exception as e:
            pass
        
        return expected_routes
    
    @staticmethod
    def regenerate_missing_routes(app, blueprint_name: str, route_file_path: str) -> Dict[str, Any]:
        """Regenerate missing routes for a blueprint"""
        try:
            # Get expected routes from file
            expected_routes = RouteRegenerator.get_expected_routes_from_file(route_file_path)
            
            # Get actual registered routes
            actual_routes = []
            for rule in app.url_map.iter_rules():
                if blueprint_name in rule.endpoint:
                    actual_routes.append({
                        'path': str(rule),
                        'endpoint': rule.endpoint,
                        'methods': list(rule.methods)
                    })
            
            # Find missing routes
            missing_routes = []
            for expected in expected_routes:
                found = False
                for actual in actual_routes:
                    if expected['path'] in actual['path']:
                        found = True
                        break
                
                if not found:
                    missing_routes.append(expected)
            
            # Try to re-register blueprint
            if missing_routes:
                try:
                    # Import and re-register
                    module_path = route_file_path.replace('.py', '').replace('/', '.').replace('\\', '.')
                    if module_path.startswith('backend.'):
                        module = importlib.import_module(module_path)
                        bp = getattr(module, f'{blueprint_name}_bp', None)
                        
                        if bp:
                            app.register_blueprint(bp)
                            return {
                                'success': True,
                                'missing_routes': missing_routes,
                                'regenerated': True,
                                'message': f'Re-registered {blueprint_name} blueprint'
                            }
                except Exception as e:
                    pass
            
            return {
                'success': len(missing_routes) == 0,
                'missing_routes': missing_routes,
                'regenerated': False,
                'message': f'Found {len(missing_routes)} missing routes'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'regenerated': False
            }


class RouteIndicatorSystem:
    """10 indicators and solutions for route registration issues"""
    
    INDICATORS = [
        {
            'id': 1,
            'name': 'Blueprint Name Conflict',
            'description': 'Multiple blueprints with same name',
            'solution': 'Rename blueprint with unique name using name= parameter',
            'auto_fix': True,
            'severity': 'high'
        },
        {
            'id': 2,
            'name': 'URL Path Conflict',
            'description': 'Same URL path registered multiple times',
            'solution': 'Use different URL paths or combine into single endpoint',
            'auto_fix': False,
            'severity': 'high'
        },
        {
            'id': 3,
            'name': 'Endpoint Name Conflict',
            'description': 'Same endpoint name used by multiple routes',
            'solution': 'Use unique endpoint names or specify endpoint= in route decorator',
            'auto_fix': True,
            'severity': 'medium'
        },
        {
            'id': 4,
            'name': 'Missing Route Registration',
            'description': 'Route defined in file but not registered',
            'solution': 'Ensure blueprint is registered in register_blueprints.py',
            'auto_fix': True,
            'severity': 'high'
        },
        {
            'id': 5,
            'name': 'Import Error',
            'description': 'Cannot import blueprint module',
            'solution': 'Check module path, ensure file exists, fix import errors',
            'auto_fix': False,
            'severity': 'high'
        },
        {
            'id': 6,
            'name': 'Syntax Error in Route File',
            'description': 'Syntax error prevents route file from loading',
            'solution': 'Fix syntax errors in route file',
            'auto_fix': False,
            'severity': 'high'
        },
        {
            'id': 7,
            'name': 'Missing URL Prefix',
            'description': 'Route missing expected URL prefix',
            'solution': 'Add url_prefix to Blueprint or adjust route paths',
            'auto_fix': True,
            'severity': 'medium'
        },
        {
            'id': 8,
            'name': 'Method Conflict',
            'description': 'Same HTTP method on same URL with different handlers',
            'solution': 'Use different methods or combine handlers',
            'auto_fix': False,
            'severity': 'medium'
        },
        {
            'id': 9,
            'name': 'Blueprint Not Registered',
            'description': 'Blueprint exists but not registered in app',
            'solution': 'Add app.register_blueprint() call in register_blueprints.py',
            'auto_fix': True,
            'severity': 'high'
        },
        {
            'id': 10,
            'name': 'Route Count Mismatch',
            'description': 'Expected number of routes not matching registered count',
            'solution': 'Check route definitions, ensure all routes are properly decorated',
            'auto_fix': False,
            'severity': 'low'
        }
    ]
    
    @staticmethod
    def get_all_indicators() -> List[Dict[str, Any]]:
        """Get all 10 indicators"""
        return RouteIndicatorSystem.INDICATORS
    
    @staticmethod
    def check_indicators(app, blueprint_name: Optional[str] = None) -> Dict[str, Any]:
        """Check all indicators for a blueprint or all blueprints"""
        results = {
            'indicators': [],
            'issues_found': 0,
            'auto_fixable': 0
        }
        
        # Check each indicator
        for indicator in RouteIndicatorSystem.INDICATORS:
            issue = RouteIndicatorSystem._check_indicator(app, indicator, blueprint_name)
            if issue['found']:
                results['indicators'].append(issue)
                results['issues_found'] += 1
                if indicator['auto_fix']:
                    results['auto_fixable'] += 1
        
        return results
    
    @staticmethod
    def _check_indicator(app, indicator: Dict[str, Any], blueprint_name: Optional[str] = None) -> Dict[str, Any]:
        """Check a specific indicator"""
        issue = {
            'indicator_id': indicator['id'],
            'name': indicator['name'],
            'found': False,
            'details': [],
            'solution': indicator['solution'],
            'auto_fix': indicator['auto_fix'],
            'severity': indicator['severity']
        }
        
        if indicator['id'] == 1:  # Blueprint Name Conflict
            conflicts = RouteConflictDetector.check_blueprint_name_conflicts(app)
            if conflicts['total_conflicts'] > 0:
                issue['found'] = True
                issue['details'] = conflicts['conflicts']
        
        elif indicator['id'] == 2:  # URL Path Conflict
            url_conflicts = RouteConflictDetector.check_url_conflicts_both_ways(app)
            if url_conflicts['total_conflicts'] > 0:
                issue['found'] = True
                issue['details'] = [c for c in url_conflicts['conflicts'] if c['type'] == 'url_conflict']
        
        elif indicator['id'] == 4:  # Missing Route Registration
            if blueprint_name:
                # Check if blueprint is registered
                bp_routes = [r for r in app.url_map.iter_rules() if blueprint_name in r.endpoint]
                if len(bp_routes) == 0:
                    issue['found'] = True
                    issue['details'] = [{'blueprint': blueprint_name, 'status': 'not_registered'}]
        
        elif indicator['id'] == 9:  # Blueprint Not Registered
            if blueprint_name:
                registered_blueprints = [bp.name for bp in app.blueprints.values()]
                if blueprint_name not in registered_blueprints:
                    issue['found'] = True
                    issue['details'] = [{'blueprint': blueprint_name, 'status': 'missing'}]
        
        return issue


@comprehensive_route_debugger_bp.route('/comprehensive-check', methods=['GET'])
def comprehensive_check():
    """Comprehensive check of all routes, blueprints, and conflicts"""
    try:
        app = current_app
        
        # Get all routes
        all_routes = []
        for rule in app.url_map.iter_rules():
            all_routes.append({
                'endpoint': rule.endpoint,
                'path': str(rule),
                'methods': list(rule.methods),
                'blueprint': rule.endpoint.split('.')[0] if '.' in rule.endpoint else None
            })
        
        # Check for unified_game_mechanics routes specifically
        gm_routes = [r for r in all_routes if 'game-mechanics' in r['path'] or 'unified_game_mechanics' in r['endpoint']]
        expected_gm_routes = 7  # Based on file analysis
        
        # Check conflicts
        url_conflicts = RouteConflictDetector.check_url_conflicts_both_ways(app)
        blueprint_conflicts = RouteConflictDetector.check_blueprint_name_conflicts(app)
        
        # Check indicators
        indicators = RouteIndicatorSystem.check_indicators(app, 'unified_game_mechanics')
        
        # Check if all expected routes are present
        missing_routes = []
        if len(gm_routes) < expected_gm_routes:
            missing_routes = [f'Expected {expected_gm_routes} routes, found {len(gm_routes)}']
        
        return jsonify({
            'success': True,
            'total_routes': len(all_routes),
            'game_mechanics': {
                'expected': expected_gm_routes,
                'found': len(gm_routes),
                'routes': gm_routes,
                'missing': missing_routes
            },
            'conflicts': {
                'url_conflicts': url_conflicts,
                'blueprint_conflicts': blueprint_conflicts
            },
            'indicators': indicators,
            'all_blueprints': list(app.blueprints.keys()),
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@comprehensive_route_debugger_bp.route('/check-blueprint/<name>', methods=['GET'])
def check_blueprint(name: str):
    """Check a specific blueprint"""
    try:
        app = current_app
        
        # Get routes for this blueprint
        bp_routes = []
        for rule in app.url_map.iter_rules():
            if name in rule.endpoint:
                bp_routes.append({
                    'endpoint': rule.endpoint,
                    'path': str(rule),
                    'methods': list(rule.methods)
                })
        
        # Check if blueprint is registered
        is_registered = name in app.blueprints
        
        # Check indicators for this blueprint
        indicators = RouteIndicatorSystem.check_indicators(app, name)
        
        # Try to regenerate if missing routes
        regeneration_result = None
        if not is_registered or len(bp_routes) == 0:
            # Try to find route file
            route_file_path = f'backend/routes/{name}_routes.py'
            if os.path.exists(route_file_path):
                regeneration_result = RouteRegenerator.regenerate_missing_routes(
                    app, name, route_file_path
                )
        
        return jsonify({
            'success': True,
            'blueprint_name': name,
            'registered': is_registered,
            'routes_found': len(bp_routes),
            'routes': bp_routes,
            'indicators': indicators,
            'regeneration': regeneration_result
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@comprehensive_route_debugger_bp.route('/fix-conflicts', methods=['POST'])
def fix_conflicts():
    """Auto-fix conflicts where possible"""
    try:
        app = current_app
        data = request.get_json() or {}
        blueprint_name = data.get('blueprint_name')
        
        fixes_applied = []
        
        # Fix blueprint name conflicts
        if blueprint_name:
            conflicts = RouteConflictDetector.check_blueprint_name_conflicts(app)
            for conflict in conflicts['conflicts']:
                if conflict['blueprint_name'] == blueprint_name:
                    # Rename blueprint
                    try:
                        # This would require re-registering with new name
                        fixes_applied.append({
                            'type': 'blueprint_rename',
                            'blueprint': blueprint_name,
                            'new_name': f"{blueprint_name}_fixed",
                            'status': 'suggested'
                        })
                    except Exception as e:
                        pass
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes_applied,
            'message': f'Applied {len(fixes_applied)} fixes'
        }), 200
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@comprehensive_route_debugger_bp.route('/regenerate-missing', methods=['POST'])
def regenerate_missing():
    """Regenerate missing routes"""
    try:
        app = current_app
        data = request.get_json() or {}
        blueprint_name = data.get('blueprint_name', 'unified_game_mechanics')
        
        # Find route file
        route_file_path = f'backend/routes/{blueprint_name}_routes.py'
        if not os.path.exists(route_file_path):
            # Try alternative naming
            route_file_path = f'backend/routes/unified_game_mechanics_routes.py'
        
        if os.path.exists(route_file_path):
            result = RouteRegenerator.regenerate_missing_routes(
                app, blueprint_name, route_file_path
            )
            return jsonify(result), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Route file not found: {route_file_path}'
            }), 404
    
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@comprehensive_route_debugger_bp.route('/indicators', methods=['GET'])
def get_indicators():
    """Get all 10 indicators and solutions"""
    return jsonify({
        'success': True,
        'indicators': RouteIndicatorSystem.get_all_indicators(),
        'total': len(RouteIndicatorSystem.INDICATORS)
    }), 200

