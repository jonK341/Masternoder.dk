"""
API Scanner Service
Scans codebase for blueprints, routes, and API endpoints
Auto-generates missing API methods and registrations
"""
import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime

class APIScanner:
    """Scans and analyzes API structure, auto-generates missing methods"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.routes_dir = os.path.join(self.base_dir, 'backend', 'routes')
        self.services_dir = os.path.join(self.base_dir, 'backend', 'services')
        self.scan_results = {
            'blueprints': [],
            'routes': [],
            'missing_methods': [],
            'suggestions': []
        }
    
    def scan_all(self) -> Dict:
        """Scan entire codebase for API structure"""
        self.scan_results = {
            'blueprints': self.scan_blueprints(),
            'routes': self.scan_routes(),
            'services': self.scan_services(),
            'missing_methods': self.find_missing_methods(),
            'suggestions': self.generate_suggestions(),
            'timestamp': datetime.now().isoformat()
        }
        return self.scan_results
    
    def scan_blueprints(self) -> List[Dict]:
        """Scan for all blueprint definitions"""
        blueprints = []
        
        if not os.path.exists(self.routes_dir):
            return blueprints
        
        for file_path in Path(self.routes_dir).glob('*.py'):
            if file_path.name.endswith('.backup'):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find blueprint definitions
                bp_matches = re.findall(r'(\w+_bp)\s*=\s*Blueprint\([\'"]([\w_]+)[\'"]', content)
                for bp_var, bp_name in bp_matches:
                    # Find routes in this blueprint
                    routes = self._extract_routes_from_file(content, bp_name)
                    
                    blueprints.append({
                        'file': str(file_path.relative_to(self.base_dir)),
                        'variable': bp_var,
                        'name': bp_name,
                        'module': f"backend.routes.{file_path.stem}",
                        'routes': routes,
                        'route_count': len(routes)
                    })
            except Exception as e:
                blueprints.append({
                    'file': str(file_path.relative_to(self.base_dir)),
                    'error': str(e)
                })
        
        return blueprints
    
    def _extract_routes_from_file(self, content: str, bp_name: str) -> List[Dict]:
        """Extract route definitions from file content"""
        routes = []
        
        # Pattern: @bp_name.route('/path', methods=['GET', 'POST'])
        pattern = rf'@\w+\.route\([\'"]([^\'"]+)[\'"]\s*(?:,\s*methods=\[([^\]]+)\])?\)'
        
        for match in re.finditer(pattern, content):
            path = match.group(1)
            methods_str = match.group(2) if match.group(2) else "'GET'"
            
            # Parse methods
            methods = re.findall(r'[\'"]([A-Z]+)[\'"]', methods_str)
            if not methods:
                methods = ['GET']
            
            # Find function name after route decorator
            func_match = re.search(rf'{re.escape(match.group(0))}\s*\n\s*def\s+(\w+)', content)
            func_name = func_match.group(1) if func_match else 'unknown'
            
            routes.append({
                'path': path,
                'methods': methods,
                'function': func_name
            })
        
        return routes
    
    def scan_routes(self) -> List[Dict]:
        """Scan for all route definitions"""
        all_routes = []
        
        for bp in self.scan_blueprints():
            if 'routes' in bp:
                for route in bp['routes']:
                    all_routes.append({
                        'blueprint': bp['name'],
                        'path': route['path'],
                        'methods': route['methods'],
                        'function': route['function'],
                        'file': bp['file']
                    })
        
        return all_routes
    
    def scan_services(self) -> List[Dict]:
        """Scan for service files"""
        services = []
        
        if not os.path.exists(self.services_dir):
            return services
        
        for file_path in Path(self.services_dir).rglob('*.py'):
            if '__pycache__' in str(file_path):
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check if it's a service (has class definition)
                class_matches = re.findall(r'class\s+(\w+)(?:\([^)]+\))?:', content)
                
                if class_matches:
                    services.append({
                        'file': str(file_path.relative_to(self.base_dir)),
                        'classes': class_matches,
                        'module': f"backend.services.{file_path.relative_to(self.services_dir).with_suffix('').as_posix().replace('/', '.')}"
                    })
            except Exception as e:
                services.append({
                    'file': str(file_path.relative_to(self.base_dir)),
                    'error': str(e)
                })
        
        return services
    
    def find_missing_methods(self) -> List[Dict]:
        """Find missing CRUD methods for blueprints"""
        missing = []
        
        for bp in self.scan_blueprints():
            if 'error' in bp:
                continue
            
            routes = bp.get('routes', [])
            route_paths = [r['path'] for r in routes]
            
            # Check for standard CRUD operations
            base_paths = self._get_base_paths(bp['name'])
            
            for base_path, methods in base_paths.items():
                for method in methods:
                    # Check if route exists
                    found = any(
                        base_path in r['path'] and method in r['methods']
                        for r in routes
                    )
                    
                    if not found:
                        missing.append({
                            'blueprint': bp['name'],
                            'path': base_path,
                            'method': method,
                            'suggested_function': self._suggest_function_name(base_path, method),
                            'file': bp['file']
                        })
        
        return missing
    
    def _get_base_paths(self, bp_name: str) -> Dict[str, List[str]]:
        """Get standard CRUD paths for a blueprint"""
        # Convert blueprint name to resource name
        resource = bp_name.replace('_bp', '').replace('_routes', '')
        
        return {
            f'/api/{resource}': ['GET', 'POST'],
            f'/api/{resource}/<id>': ['GET', 'PUT', 'DELETE'],
            f'/api/{resource}/list': ['GET'],
            f'/api/{resource}/create': ['POST'],
            f'/api/{resource}/update/<id>': ['PUT'],
            f'/api/{resource}/delete/<id>': ['DELETE']
        }
    
    def _suggest_function_name(self, path: str, method: str) -> str:
        """Suggest function name based on path and method"""
        # Extract resource from path
        resource = path.split('/')[-1].replace('<', '').replace('>', '').replace('id', '')
        if not resource:
            resource = path.split('/')[-2]
        
        method_lower = method.lower()
        
        if method_lower == 'get':
            if '<id>' in path or '/<id>' in path:
                return f'get_{resource}_by_id'
            elif 'list' in path:
                return f'list_{resource}s'
            else:
                return f'get_{resource}'
        elif method_lower == 'post':
            return f'create_{resource}'
        elif method_lower == 'put':
            return f'update_{resource}'
        elif method_lower == 'delete':
            return f'delete_{resource}'
        else:
            return f'{method_lower}_{resource}'
    
    def generate_suggestions(self) -> List[Dict]:
        """Generate suggestions for missing API methods"""
        suggestions = []
        
        for missing in self.find_missing_methods():
            suggestion = self._generate_method_code(missing)
            suggestions.append({
                'blueprint': missing['blueprint'],
                'missing': missing,
                'code': suggestion
            })
        
        return suggestions
    
    def _generate_method_code(self, missing: Dict) -> str:
        """Generate code for missing method"""
        bp_name = missing['blueprint']
        path = missing['path']
        method = missing['method']
        func_name = missing['suggested_function']
        
        code = f"""
@{{bp_name}}.route('{path}', methods=['{method}'])
@{{bp_name}}.route('/vidgenerator{path}', methods=['{method}'])
def {func_name}():
    \"\"\"{method} endpoint for {path}\"\"\"
    try:
        from flask import request, jsonify
        
"""
        
        if method == 'GET':
            if '<id>' in path:
                code += f"""        item_id = request.view_args.get('id')
        # TODO: Fetch item by ID from database
        return jsonify({{
            'success': True,
            'data': {{'id': item_id}},
            'message': 'Item retrieved successfully'
        }}), 200
"""
            else:
                code += f"""        # TODO: Fetch list of items
        return jsonify({{
            'success': True,
            'data': [],
            'message': 'Items retrieved successfully'
        }}), 200
"""
        elif method == 'POST':
            code += f"""        data = request.get_json() or {{}}
        # TODO: Create new item from data
        return jsonify({{
            'success': True,
            'data': data,
            'message': 'Item created successfully'
        }}), 201
"""
        elif method == 'PUT':
            code += f"""        item_id = request.view_args.get('id')
        data = request.get_json() or {{}}
        # TODO: Update item by ID
        return jsonify({{
            'success': True,
            'data': {{'id': item_id, **data}},
            'message': 'Item updated successfully'
        }}), 200
"""
        elif method == 'DELETE':
            code += f"""        item_id = request.view_args.get('id')
        # TODO: Delete item by ID
        return jsonify({{
            'success': True,
            'message': 'Item deleted successfully'
        }}), 200
"""
        
        code += """    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500
"""
        
        return code
    
    def auto_generate_missing_methods(self, blueprint_name: Optional[str] = None) -> Dict:
        """Auto-generate and add missing methods to blueprint files"""
        results = {
            'generated': [],
            'errors': [],
            'files_modified': []
        }
        
        missing = self.find_missing_methods()
        
        if blueprint_name:
            missing = [m for m in missing if m['blueprint'] == blueprint_name]
        
        for item in missing:
            try:
                file_path = os.path.join(self.base_dir, item['file'])
                
                # Read file
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Generate method code
                method_code = self._generate_method_code(item)
                
                # Find insertion point (before last function or at end)
                # Insert before the last closing of the file
                insertion_point = content.rfind('\n\n')
                if insertion_point == -1:
                    insertion_point = len(content)
                
                # Add method code
                new_content = content[:insertion_point] + method_code + content[insertion_point:]
                
                # Write back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                results['generated'].append({
                    'blueprint': item['blueprint'],
                    'path': item['path'],
                    'method': item['method'],
                    'file': item['file']
                })
                
                if item['file'] not in results['files_modified']:
                    results['files_modified'].append(item['file'])
                    
            except Exception as e:
                results['errors'].append({
                    'blueprint': item['blueprint'],
                    'error': str(e)
                })
        
        return results
    
    def generate_registration_code(self) -> str:
        """Generate blueprint registration code"""
        blueprints = self.scan_blueprints()
        
        code = """def register_all_blueprints(app):
    \"\"\"Register all blueprints automatically\"\"\"
    registered_count = 0
    
"""
        
        for bp in blueprints:
            if 'error' in bp:
                continue
            
            code += f"""    # {bp['name']}
    try:
        from {bp['module']} import {bp['variable']}
        app.register_blueprint({bp['variable']})
        registered_count += 1
        print("  [OK] Registered {bp['name']} blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import {bp['name']}: {{e}}")
    except Exception as e:
        print(f"  [ERROR] Error registering {bp['name']}: {{e}}")
    
"""
        
        code += """    print(f"\\n  [SUMMARY] Registered {registered_count} blueprints")
    return registered_count
"""
        
        return code
    
    def get_report(self) -> Dict:
        """Get comprehensive scan report"""
        scan_results = self.scan_all()
        
        return {
            'summary': {
                'total_blueprints': len(scan_results['blueprints']),
                'total_routes': len(scan_results['routes']),
                'total_services': len(scan_results['services']),
                'missing_methods': len(scan_results['missing_methods']),
                'suggestions': len(scan_results['suggestions'])
            },
            'blueprints': scan_results['blueprints'],
            'routes': scan_results['routes'],
            'services': scan_results['services'],
            'missing_methods': scan_results['missing_methods'],
            'suggestions': scan_results['suggestions'],
            'timestamp': scan_results['timestamp']
        }

# Global instance
api_scanner = APIScanner()
