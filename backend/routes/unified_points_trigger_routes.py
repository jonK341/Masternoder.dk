"""
Unified Points Trigger Routes
API endpoints for unified points trigger integration.
All endpoints resolve user_id via session > body > identification.
"""
from flask import Blueprint, jsonify, request
from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
from backend.services.account_resolution_service import resolve_user_id

unified_points_trigger_bp = Blueprint('unified_points_trigger', __name__)

@unified_points_trigger_bp.route('/api/points/trigger/award', methods=['POST'])
def award_points_with_trigger():
    """Award points with automatic trigger"""
    try:
        data = request.get_json() or {}
        point_type = data.get('point_type')
        user_id = resolve_user_id(from_body=True, from_query=False)
        amount = data.get('amount', 1)
        metadata = data.get('metadata', {})
        
        if not point_type:
            return jsonify({
                'success': False,
                'error': 'point_type required'
            }), 400
        
        result = unified_points_trigger_integration.award_points_with_trigger(
            point_type, user_id, amount, metadata
        )
        try:
            from backend.services.ai_user_controller import on_user_activity
            activity = "xp_earned" if "xp" in point_type else point_type.replace("_points", "_earned")
            on_user_activity(user_id, activity, {"amount": amount, "point_type": point_type})
        except Exception:
            pass
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_points_trigger_bp.route('/api/points/trigger/award-multiple', methods=['POST'])
def award_multiple_points():
    """Award multiple point types with triggers"""
    try:
        data = request.get_json() or {}
        points = data.get('points', {})
        user_id = resolve_user_id(from_body=True, from_query=False)
        metadata = data.get('metadata', {})
        
        if not points:
            return jsonify({
                'success': False,
                'error': 'points dictionary required'
            }), 400
        
        result = unified_points_trigger_integration.award_multiple_points(
            points, user_id, metadata
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@unified_points_trigger_bp.route('/api/points/trigger/mapping', methods=['GET'])
def get_trigger_mapping():
    """Get trigger mapping for all point types"""
    try:
        return jsonify({
            'success': True,
            'mapping': unified_points_trigger_integration.trigger_mapping,
            'total_mappings': len(unified_points_trigger_integration.trigger_mapping)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
