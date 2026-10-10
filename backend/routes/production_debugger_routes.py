"""
Production Debugger Routes
API endpoints for production debugging and monitoring
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)
production_debugger_bp = Blueprint('production_debugger', __name__)

try:
    from backend.services.production_debugger import production_debugger
except ImportError:
    production_debugger = None
    logger.warning("Production debugger not available")


@production_debugger_bp.route('/api/debug/system/<system_name>', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/system/<system_name>', methods=['GET'])
def debug_system(system_name):
    """Debug a specific system"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        result = production_debugger.debug_system(system_name)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error debugging system {system_name}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/route', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/route', methods=['GET'])
def debug_route():
    """Debug a specific route"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        route_path = request.args.get('path', '')
        blueprint_name = request.args.get('blueprint', None)
        
        result = production_debugger.debug_route(route_path, blueprint_name)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error debugging route: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/frontend', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/frontend', methods=['GET'])
def debug_frontend():
    """Debug a frontend page"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        page_path = request.args.get('path', '')
        
        result = production_debugger.debug_frontend(page_path)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error debugging frontend: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/all-systems', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/all-systems', methods=['GET'])
def debug_all_systems():
    """Debug all systems"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        results = production_debugger.debug_all_systems()
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        }), 200
    except Exception as e:
        logger.error(f"Error debugging all systems: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/all-routes', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/all-routes', methods=['GET'])
def debug_all_routes():
    """Debug all routes"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        results = production_debugger.debug_all_routes()
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        }), 200
    except Exception as e:
        logger.error(f"Error debugging all routes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/test-url', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/test-url', methods=['GET'])
def test_url():
    """Test a URL endpoint"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        url = request.args.get('url', '')
        if not url:
            return jsonify({
                'success': False,
                'error': 'URL parameter required'
            }), 200
        
        result = production_debugger.test_url(url)
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error testing URL: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/test-all-routes', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/test-all-routes', methods=['GET'])
def test_all_routes():
    """Test all registered routes"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        base_url = request.args.get('base_url', 'https://masternoder.dk')
        results = production_debugger.test_all_routes(base_url)
        return jsonify({
            'success': True,
            'results': results
        }), 200
    except Exception as e:
        logger.error(f"Error testing all routes: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/find-broken-urls', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/find-broken-urls', methods=['GET'])
def find_broken_urls():
    """Find broken URLs from a list"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        # Get URLs from query parameter (comma-separated) or from test_all_routes
        urls_param = request.args.get('urls', '')
        if urls_param:
            urls = [u.strip() for u in urls_param.split(',')]
        else:
            # Get from test_all_routes
            base_url = request.args.get('base_url', 'https://masternoder.dk')
            test_results = production_debugger.test_all_routes(base_url)
            urls = [r['url'] for r in test_results.get('routes', [])]
        
        broken = production_debugger.find_broken_urls(urls)
        return jsonify({
            'success': True,
            'broken': broken,
            'total': len(broken)
        }), 200
    except Exception as e:
        logger.error(f"Error finding broken URLs: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/check-duplicates', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/check-duplicates', methods=['GET'])
def check_duplicates():
    """Check for duplicate blueprint registrations"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        result = production_debugger.check_duplicate_blueprints()
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        logger.error(f"Error checking duplicates: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@production_debugger_bp.route('/api/debug/report', methods=['GET'])
@production_debugger_bp.route('/vidgenerator/api/debug/report', methods=['GET'])
def get_debug_report():
    """Get comprehensive debug report"""
    try:
        if not production_debugger:
            return jsonify({
                'success': False,
                'error': 'Production debugger not available'
            }), 200
        
        report = production_debugger.generate_report()
        return jsonify({
            'success': True,
            'report': report,
            'system_status': production_debugger.system_status,
            'route_status': production_debugger.route_status,
            'frontend_status': production_debugger.frontend_status,
            'url_test_results': production_debugger.url_test_results,
            'fixes_applied': production_debugger.fixes_applied
        }), 200
    except Exception as e:
        logger.error(f"Error generating debug report: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200
