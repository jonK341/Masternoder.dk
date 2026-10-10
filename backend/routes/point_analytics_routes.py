"""
Point Analytics API Routes
"""
from flask import Blueprint, request, jsonify
# Import services - optional
try:
    from backend.services.point_analytics_dashboard import point_analytics_dashboard
except ImportError:
    point_analytics_dashboard = None
try:
    from backend.services.point_history_tracking import point_history_tracking
except ImportError:
    point_history_tracking = None
try:
    from backend.services.point_calculator_integration import point_calculator_integration
except ImportError:
    point_calculator_integration = None

point_analytics_bp = Blueprint('point_analytics', __name__)

@point_analytics_bp.route('/api/points/analytics/comprehensive', methods=['GET'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/comprehensive', methods=['GET'])
def get_comprehensive_analytics():
    """Get comprehensive point analytics"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        days = int(request.args.get('days', 30))
        
        result = point_analytics_dashboard.get_comprehensive_analytics(user_id, days)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@point_analytics_bp.route('/api/points/analytics/point-type', methods=['GET'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/point-type', methods=['GET'])
def get_point_type_analytics():
    """Get analytics for a specific point type"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        point_type = request.args.get('point_type')
        days = int(request.args.get('days', 30))
        
        if not point_type:
            return jsonify({'success': False, 'error': 'point_type required'}), 400
        
        result = point_analytics_dashboard.get_point_type_analytics(user_id, point_type, days)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@point_analytics_bp.route('/api/points/analytics/history', methods=['GET'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/history', methods=['GET'])
def get_point_history():
    """Get point history"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        point_type = request.args.get('point_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        limit = int(request.args.get('limit', 100))
        
        result = point_history_tracking.get_point_history(
            user_id, point_type, start_date, end_date, limit
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@point_analytics_bp.route('/api/points/statistics', methods=['GET'])
@point_analytics_bp.route('/api/points/analytics/statistics', methods=['GET'])
@point_analytics_bp.route('/vidgenerator/api/points/statistics', methods=['GET'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/statistics', methods=['GET'])
def get_point_statistics():
    """Get point statistics"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        point_type = request.args.get('point_type')
        days = int(request.args.get('days', 30))
        
        result = point_history_tracking.get_point_statistics(user_id, point_type, days)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@point_analytics_bp.route('/api/points/analytics/calculate', methods=['POST'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/calculate', methods=['POST'])
def calculate_points():
    """Calculate points with atomic precision"""
    try:
        data = request.get_json() or {}
        base_points = float(data.get('base_points', 0))
        multipliers = data.get('multipliers', {})
        
        result = point_calculator_integration.calculate_points_with_precision(
            base_points, multipliers
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@point_analytics_bp.route('/api/points/analytics/calculate-bonuses', methods=['POST'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/calculate-bonuses', methods=['POST'])
def calculate_bonuses():
    """Calculate point bonuses"""
    try:
        data = request.get_json() or {}
        base_points = float(data.get('base_points', 0))
        quality = float(data.get('quality', 1.0))
        difficulty = float(data.get('difficulty', 1.0))
        streak = int(data.get('streak', 0))
        level = int(data.get('level', 1))
        
        result = point_calculator_integration.calculate_point_bonuses(
            base_points, quality, difficulty, streak, level
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@point_analytics_bp.route('/api/points/analytics/record-change', methods=['POST'])
@point_analytics_bp.route('/vidgenerator/api/points/analytics/record-change', methods=['POST'])
def record_point_change():
    """Record a point change in history"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        point_type = data.get('point_type')
        amount = float(data.get('amount', 0))
        source = data.get('source', 'unknown')
        metadata = data.get('metadata', {})
        
        if not point_type:
            return jsonify({'success': False, 'error': 'point_type required'}), 400
        
        result = point_history_tracking.record_point_change(
            user_id, point_type, amount, source, metadata
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

