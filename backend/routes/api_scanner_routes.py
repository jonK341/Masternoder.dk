"""
API Scanner Routes
Provides API endpoints for the API scanner debugger tool
"""
from flask import Blueprint, jsonify, request
from backend.services.api_scanner import api_scanner

api_scanner_bp = Blueprint('api_scanner', __name__)

@api_scanner_bp.route('/api/debugger/scanner/scan', methods=['GET'])
def scan_all():
    """Scan entire codebase for API structure"""
    try:
        report = api_scanner.get_report()
        return jsonify({
            'success': True,
            'report': report
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/blueprints', methods=['GET'])
def get_blueprints():
    """Get all blueprints"""
    try:
        blueprints = api_scanner.scan_blueprints()
        return jsonify({
            'success': True,
            'blueprints': blueprints,
            'count': len(blueprints)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/routes', methods=['GET'])
def get_routes():
    """Get all routes"""
    try:
        routes = api_scanner.scan_routes()
        return jsonify({
            'success': True,
            'routes': routes,
            'count': len(routes)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/missing', methods=['GET'])
def get_missing_methods():
    """Get missing API methods"""
    try:
        missing = api_scanner.find_missing_methods()
        return jsonify({
            'success': True,
            'missing': missing,
            'count': len(missing)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/suggestions', methods=['GET'])
def get_suggestions():
    """Get code suggestions for missing methods"""
    try:
        suggestions = api_scanner.generate_suggestions()
        return jsonify({
            'success': True,
            'suggestions': suggestions,
            'count': len(suggestions)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/generate', methods=['POST'])
def generate_methods():
    """Auto-generate missing API methods"""
    try:
        data = request.get_json() or {}
        blueprint_name = data.get('blueprint', None)
        dry_run = data.get('dry_run', False)
        
        if dry_run:
            # Just return what would be generated
            missing = api_scanner.find_missing_methods()
            if blueprint_name:
                missing = [m for m in missing if m['blueprint'] == blueprint_name]
            
            suggestions = []
            for item in missing:
                code = api_scanner._generate_method_code(item)
                suggestions.append({
                    'blueprint': item['blueprint'],
                    'path': item['path'],
                    'method': item['method'],
                    'code': code
                })
            
            return jsonify({
                'success': True,
                'dry_run': True,
                'would_generate': suggestions,
                'count': len(suggestions)
            }), 200
        else:
            # Actually generate and write
            results = api_scanner.auto_generate_missing_methods(blueprint_name)
            return jsonify({
                'success': True,
                'dry_run': False,
                'results': results
            }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/registration-code', methods=['GET'])
def get_registration_code():
    """Get auto-generated blueprint registration code"""
    try:
        code = api_scanner.generate_registration_code()
        return jsonify({
            'success': True,
            'code': code
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@api_scanner_bp.route('/api/debugger/scanner/services', methods=['GET'])
def get_services():
    """Get all services"""
    try:
        services = api_scanner.scan_services()
        return jsonify({
            'success': True,
            'services': services,
            'count': len(services)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
