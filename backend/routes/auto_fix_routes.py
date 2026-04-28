"""
Auto-Fix Routes
API endpoints for managing and viewing auto-fixed endpoints
"""
from flask import Blueprint, jsonify, request
from backend.services.auto_fix_endpoints import auto_fix_endpoints

auto_fix_bp = Blueprint('auto_fix', __name__)

@auto_fix_bp.route('/api/auto-fix/endpoints', methods=['GET'])
def get_fixed_endpoints():
    """Get list of all auto-fixed endpoints"""
    try:
        fixed = auto_fix_endpoints.get_fixed_endpoints()
        stats = auto_fix_endpoints.get_statistics()
        
        return jsonify({
            'success': True,
            'fixed_endpoints': fixed,
            'statistics': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auto_fix_bp.route('/api/auto-fix/patterns', methods=['GET'])
def get_404_patterns():
    """Get 404 patterns for analysis"""
    try:
        patterns = auto_fix_endpoints.get_404_patterns()
        
        return jsonify({
            'success': True,
            'patterns': patterns
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auto_fix_bp.route('/api/auto-fix/statistics', methods=['GET'])
def get_statistics():
    """Get auto-fix statistics"""
    try:
        stats = auto_fix_endpoints.get_statistics()
        
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@auto_fix_bp.route('/api/auto-fix/manual-fix', methods=['POST'])
def manual_fix_endpoint():
    """Manually trigger auto-fix for an endpoint"""
    try:
        data = request.get_json() or {}
        path = data.get('path') or request.args.get('path')
        method = data.get('method', 'GET')
        
        if not path:
            return jsonify({
                'success': False,
                'error': 'path is required'
            }), 400
        
        response_data, status_code = auto_fix_endpoints.auto_fix_endpoint(path, method)
        
        if response_data:
            return jsonify({
                'success': True,
                'message': 'Endpoint auto-fixed',
                'response': response_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Endpoint does not meet auto-fix criteria'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
