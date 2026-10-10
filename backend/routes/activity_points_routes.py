"""
Activity Points API Routes
"""
from flask import Blueprint, request, jsonify

# Import services with error handling
try:
    from backend.services.activity_points_system import activity_points_system
except ImportError as e:
    print(f"WARNING: Could not import activity_points_system: {e}")
    activity_points_system = None

# Import utilities with error handling
try:
    from src.utils.input_validator import InputValidator
except ImportError:
    InputValidator = None

try:
    from src.utils.error_handler import ErrorHandler
except ImportError:
    ErrorHandler = None

try:
    from src.utils.rate_limiter import rate_limit
except ImportError:
    def rate_limit():
        def decorator(func):
            return func
        return decorator

activity_points_bp = Blueprint('activity_points_bp', __name__)

# Debug: Print when module is loaded
print(f"[ActivityPointsRoutes] Module loaded, blueprint created: {activity_points_bp.name}", flush=True)

@activity_points_bp.route('/api/activity-points/test', methods=['GET'], strict_slashes=False)
@activity_points_bp.route('/vidgenerator/api/activity-points/test', methods=['GET'], strict_slashes=False)
def test_endpoint():
    """Simple test endpoint"""
    print("[ActivityPointsRoutes] test_endpoint called", flush=True)
    return jsonify({'success': True, 'message': 'Activity points blueprint is working'}), 200


@activity_points_bp.route('/api/activity-points/track', methods=['POST'])
@activity_points_bp.route('/vidgenerator/api/activity-points/track', methods=['POST'])
@rate_limit()
def track_activity():
    """Track visitor activity and award points"""
    try:
        data = InputValidator.get_json_safe(default={})
        visitor_id = InputValidator.sanitize_string(data.get('visitor_id', ''), max_length=100)
        activity_type = InputValidator.sanitize_string(data.get('activity_type', 'page_view'), max_length=50)
        metadata = data.get('metadata', {})
        
        if not visitor_id:
            return jsonify({'success': False, 'error': 'visitor_id required'}), 400
        
        if not activity_points_system:
            return jsonify({'success': False, 'error': 'Activity points system not available'}), 500
        
        result = activity_points_system.track_visitor(visitor_id, activity_type, metadata)
        return jsonify(result), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in track_activity: {e}\n{error_trace}", flush=True)
        if ErrorHandler:
            return ErrorHandler.create_error_response(str(e), 500)
        return jsonify({'success': False, 'error': str(e), 'traceback': error_trace}), 500


@activity_points_bp.route('/api/activity-points/track-time', methods=['POST'])
@activity_points_bp.route('/vidgenerator/api/activity-points/track-time', methods=['POST'])
@rate_limit()
def track_time_spent():
    """Track time spent on page"""
    try:
        data = InputValidator.get_json_safe(default={})
        visitor_id = InputValidator.sanitize_string(data.get('visitor_id', ''), max_length=100)
        seconds = int(data.get('seconds', 0))
        
        if not visitor_id:
            return jsonify({'success': False, 'error': 'visitor_id required'}), 400
        
        result = activity_points_system.track_time_spent(visitor_id, seconds)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@activity_points_bp.route('/api/activity-points/stats/<visitor_id>', methods=['GET'])
@activity_points_bp.route('/vidgenerator/api/activity-points/stats/<visitor_id>', methods=['GET'])
@rate_limit()
def get_visitor_stats(visitor_id):
    """Get visitor statistics"""
    try:
        visitor_id = InputValidator.sanitize_string(visitor_id, max_length=100)
        result = activity_points_system.get_visitor_stats(visitor_id)
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@activity_points_bp.route('/api/activity-points/leaderboard', methods=['GET'], strict_slashes=False)
@activity_points_bp.route('/vidgenerator/api/activity-points/leaderboard', methods=['GET'], strict_slashes=False)
def get_leaderboard():
    """Get activity points leaderboard"""
    try:
        print("get_leaderboard called", flush=True)
        limit = int(request.args.get('limit', 100))
        print(f"Limit: {limit}", flush=True)
        leaderboard = activity_points_system.get_leaderboard(limit)
        print(f"Leaderboard: {leaderboard}", flush=True)
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        }), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in get_leaderboard: {e}\n{error_trace}", flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500

