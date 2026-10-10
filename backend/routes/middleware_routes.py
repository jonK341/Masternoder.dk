"""
Middleware Routes
Routes for all 150 middleware services with frontend and backend controls
"""
from flask import Blueprint, request, jsonify
from typing import Dict, Any
import logging
from backend.middleware.service_registry import middleware_service_registry

logger = logging.getLogger(__name__)

middleware_bp = Blueprint('middleware', __name__, url_prefix='/api/middleware')

@middleware_bp.route('/services', methods=['GET'])
def list_services():
    """List all registered middleware services"""
    try:
        services = []
        for service_id, service_info in middleware_service_registry.services.items():
            services.append({
                'id': service_id,
                'type': service_info['type'],
                'category': service_info['category'],
                'description': service_info['description'],
                'status': service_info['status'],
                'connections': len(middleware_service_registry.get_connected_services(service_id))
            })
        
        return jsonify({
            'success': True,
            'total_services': len(services),
            'services': services
        })
    except Exception as e:
        logger.error(f"Error listing services: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/services/<service_id>', methods=['GET'])
def get_service(service_id: str):
    """Get information about a specific service"""
    try:
        service = middleware_service_registry.get_service(service_id)
        if not service:
            return jsonify({'success': False, 'error': 'Service not found'}), 404
        
        connected = middleware_service_registry.get_connected_services(service_id)
        
        return jsonify({
            'success': True,
            'service': {
                'id': service['id'],
                'type': service['type'],
                'category': service['category'],
                'description': service['description'],
                'status': service['status'],
                'call_count': service['call_count'],
                'error_count': service['error_count'],
                'connected_services': connected,
                'connection_count': len(connected)
            }
        })
    except Exception as e:
        logger.error(f"Error getting service {service_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/services/<service_id>/call', methods=['POST'])
def call_service(service_id: str):
    """Call a middleware service"""
    try:
        data = request.get_json() or {}
        method = data.get('method', 'process')
        params = data.get('params', {})
        
        # Determine if frontend or backend call
        if method.startswith('frontend_'):
            result = middleware_service_registry.call_service(
                service_id, method, params
            )
        elif method.startswith('backend_'):
            result = middleware_service_registry.call_service(
                service_id, method, params
            )
        else:
            # Default to frontend
            result = middleware_service_registry.call_service(
                service_id, f'frontend_{method}', params
            )
        
        return jsonify({
            'success': True,
            'service_id': service_id,
            'method': method,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error calling service {service_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/services/<service_id>/frontend', methods=['POST'])
def frontend_call(service_id: str):
    """Frontend-specific service call"""
    try:
        data = request.get_json() or {}
        
        result = middleware_service_registry.call_service(
            service_id, 'frontend_process_request', data
        )
        
        return jsonify({
            'success': True,
            'service_id': service_id,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error in frontend call to {service_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/services/<service_id>/backend', methods=['POST'])
def backend_call(service_id: str):
    """Backend-specific service call"""
    try:
        data = request.get_json() or {}
        
        result = middleware_service_registry.call_service(
            service_id, 'backend_process_data', data
        )
        
        return jsonify({
            'success': True,
            'service_id': service_id,
            'result': result
        })
    except Exception as e:
        logger.error(f"Error in backend call to {service_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/services/<service_id>/connections', methods=['GET'])
def get_connections(service_id: str):
    """Get all services connected to a given service"""
    try:
        connected = middleware_service_registry.get_connected_services(service_id)
        
        return jsonify({
            'success': True,
            'service_id': service_id,
            'connected_services': connected,
            'connection_count': len(connected),
            'max_connections': middleware_service_registry.max_connections
        })
    except Exception as e:
        logger.error(f"Error getting connections for {service_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/services/<service_id1>/connect/<service_id2>', methods=['POST'])
def connect_services(service_id1: str, service_id2: str):
    """Connect two services"""
    try:
        connection_type = request.args.get('type', 'bidirectional')
        success = middleware_service_registry.connect_services(
            service_id1, service_id2, connection_type
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Connected {service_id1} and {service_id2}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to connect services'
            }), 400
    except Exception as e:
        logger.error(f"Error connecting services: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/categories', methods=['GET'])
def list_categories():
    """List all service categories"""
    try:
        categories = {}
        for service_id, service_info in middleware_service_registry.services.items():
            category = service_info['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(service_id)
        
        return jsonify({
            'success': True,
            'categories': {
                cat: {
                    'count': len(services),
                    'services': services
                }
                for cat, services in categories.items()
            }
        })
    except Exception as e:
        logger.error(f"Error listing categories: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get middleware registry statistics"""
    try:
        stats = middleware_service_registry.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@middleware_bp.route('/batch-call', methods=['POST'])
def batch_call():
    """Call multiple services in batch"""
    try:
        data = request.get_json() or {}
        service_ids = data.get('service_ids', [])
        method = data.get('method', 'process')
        params = data.get('params', {})
        
        results = {}
        for service_id in service_ids:
            try:
                result = middleware_service_registry.call_service(
                    service_id, method, params
                )
                results[service_id] = {'success': True, 'result': result}
            except Exception as e:
                results[service_id] = {'success': False, 'error': str(e)}
        
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        logger.error(f"Error in batch call: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Individual service routes (auto-generated for all 150 services)
def create_service_routes():
    """Create individual routes for each service"""
    from backend.middleware.service_generator import SERVICE_DEFINITIONS
    
    for service_def in SERVICE_DEFINITIONS:
        service_id = service_def['id']
        
        def make_service_route(sid):
            """Create a route handler for a specific service"""
            def service_route():
                """Individual service route"""
                try:
                    if request.method == 'GET':
                        service = middleware_service_registry.get_service(sid)
                        if not service:
                            return jsonify({'success': False, 'error': 'Service not found'}), 404
                        return jsonify({'success': True, 'service': service})
                    else:
                        data = request.get_json() or {}
                        result = middleware_service_registry.call_service(
                            sid, 'frontend_process_request', data
                        )
                        return jsonify({'success': True, 'result': result})
                except Exception as e:
                    logger.error(f"Error in service route {sid}: {e}")
                    return jsonify({'success': False, 'error': str(e)}), 500
            return service_route
        
        # Register the route
        middleware_bp.add_url_rule(
            f'/{service_id}',
            f'service_{service_id}',
            make_service_route(service_id),
            methods=['GET', 'POST']
        )

# Initialize routes
create_service_routes()
