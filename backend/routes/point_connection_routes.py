"""
Point Connection API Routes
Systematic solution to connect all points
"""
from flask import Blueprint, request, jsonify
from backend.services.point_connection_system import point_connection
import sys

point_connection_bp = Blueprint('point_connection', __name__)


@point_connection_bp.route('/api/points/connect-all', methods=['POST'], strict_slashes=False)
def connect_all_points():
    """Connect all points from all systems"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        
        result = point_connection.connect_all_points(user_id)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        print(f"[PointConnection] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@point_connection_bp.route('/api/points/ensure-counting', methods=['POST'], strict_slashes=False)
def ensure_point_counting():
    """Ensure a point is counted in all systems"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        point_type = data.get('point_type')
        points = data.get('points', 0)
        source = data.get('source', 'unknown')
        
        if not point_type:
            return jsonify({'success': False, 'error': 'point_type required'}), 400
        
        success = point_connection.ensure_point_counting(user_id, point_type, points, source)
        
        return jsonify({
            'success': success,
            'message': 'Point counting ensured' if success else 'Failed to ensure point counting'
        }), 200 if success else 500
    except Exception as e:
        print(f"[PointConnection] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@point_connection_bp.route('/api/points/get-all-connected', methods=['GET'], strict_slashes=False)
@point_connection_bp.route('/vidgenerator/api/points/get-all-connected', methods=['GET'], strict_slashes=False)
def get_all_connected_points():
    """Get all connected points for a user"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        result = point_connection.get_all_connected_points(user_id)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        print(f"[PointConnection] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@point_connection_bp.route('/api/points/verify-connections', methods=['GET'], strict_slashes=False)
def verify_connections():
    """Verify that all points are properly connected"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        
        verification = point_connection.verify_all_points_connected(user_id)
        
        return jsonify({
            'success': True,
            'verification': verification
        }), 200
    except Exception as e:
        print(f"[PointConnection] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@point_connection_bp.route('/api/points/test', methods=['GET'], strict_slashes=False)
def test_endpoint():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Point Connection API is working',
        'endpoints': {
            'connect_all': '/api/points/connect-all (POST)',
            'ensure_counting': '/api/points/ensure-counting (POST)',
            'get_all_connected': '/api/points/get-all-connected?user_id=USER_ID',
            'verify_connections': '/api/points/verify-connections?user_id=USER_ID'
        }
    }), 200

