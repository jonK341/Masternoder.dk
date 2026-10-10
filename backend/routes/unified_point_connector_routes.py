"""
Unified Point Connector Routes - Connect ALL point systems
"""
from flask import Blueprint, request, jsonify
from backend.services.unified_point_connector import unified_point_connector
from src.utils.rate_limiter import rate_limit
import sys

unified_connector_bp = Blueprint('unified_connector', __name__)

@unified_connector_bp.route('/api/points/connect-all', methods=['POST'])
@unified_connector_bp.route('/vidgenerator/api/points/connect-all', methods=['POST'])
@rate_limit()
def connect_all_points():
    """Connect all point systems"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        result = unified_point_connector.connect_all_systems(user_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[UnifiedConnector] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_connector_bp.route('/api/points/unified', methods=['GET'])
@unified_connector_bp.route('/vidgenerator/api/points/unified', methods=['GET'])
@rate_limit()
def get_unified_points():
    """Get unified points for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = unified_point_connector.get_unified_points(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

