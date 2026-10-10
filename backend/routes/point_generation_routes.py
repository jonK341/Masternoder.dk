"""
Point Generation Routes
API for generating points from activities
"""
from flask import Blueprint, jsonify, request
from backend.services.point_generation_activities import point_generation_activities

point_generation_bp = Blueprint('point_generation', __name__)


@point_generation_bp.route('/api/points/generate-from-activity', methods=['POST'])
@point_generation_bp.route('/vidgenerator/api/points/generate-from-activity', methods=['POST'])
def generate_points_from_activity():
    """Generate points from an activity"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        activity_type = data.get('activity_type')
        metadata = data.get('metadata', {})
        
        if not activity_type:
            return jsonify({'success': False, 'error': 'activity_type required'}), 400
        
        result = point_generation_activities.generate_points_from_activity(
            user_id, activity_type, metadata
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@point_generation_bp.route('/api/points/activity-history', methods=['GET'])
@point_generation_bp.route('/vidgenerator/api/points/activity-history', methods=['GET'])
def get_activity_history():
    """Get activity history"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 50))
        
        result = point_generation_activities.get_activity_history(user_id, limit)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@point_generation_bp.route('/api/points/activity-statistics', methods=['GET'])
@point_generation_bp.route('/vidgenerator/api/points/activity-statistics', methods=['GET'])
def get_activity_statistics():
    """Get activity statistics"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        result = point_generation_activities.get_activity_statistics(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

