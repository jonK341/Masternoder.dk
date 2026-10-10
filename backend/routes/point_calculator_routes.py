"""
Point Calculator Routes - Hardcoded Calculator Integration
API endpoints for hardcoded point calculator
"""
from flask import Blueprint, request, jsonify
# Import services - optional
try:
    from backend.services.point_calculator_integration import point_calculator_integration
except ImportError:
    point_calculator_integration = None
# Import utils - optional
try:
    from src.utils.input_validator import InputValidator
except ImportError:
    InputValidator = None
try:
    from src.utils.error_handler import ErrorHandler
except ImportError:
    ErrorHandler = None
# Import rate limiter - optional
try:
    from src.utils.rate_limiter import rate_limit
except ImportError:
    def rate_limit():
        def decorator(f):
            return f
        return decorator
import uuid

point_calculator_bp = Blueprint('point_calculator', __name__)

def get_user_id():
    """Get user ID from session or request"""
    from flask import session
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session.get('user_id', request.args.get('user_id', 'anonymous'))


@point_calculator_bp.route('/api/points/calculator/calculate', methods=['GET'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/calculate', methods=['GET'])
@rate_limit()
def calculate_points():
    """Calculate points using hardcoded calculator"""
    try:
        user_id = get_user_id()
        sync_to_db = request.args.get('sync', 'true').lower() == 'true'
        
        result = point_calculator_integration.calculate_with_hardcoded(user_id, sync_to_db=sync_to_db)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@point_calculator_bp.route('/api/points/calculator/breakdown/<user_id>', methods=['GET'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/breakdown/<user_id>', methods=['GET'])
@rate_limit()
def get_breakdown(user_id: str):
    """Get detailed point breakdown from hardcoded calculator"""
    try:
        result = point_calculator_integration.calculate_with_hardcoded(user_id, sync_to_db=False)
        
        if result.get('success'):
            calculation = result.get('calculation', {})
            return jsonify({
                'success': True,
                'user_id': user_id,
                'breakdown': calculation
            }), 200
        else:
            return jsonify(result), 500
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@point_calculator_bp.route('/api/points/calculator/verify/<user_id>', methods=['GET'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/verify/<user_id>', methods=['GET'])
@rate_limit()
def verify_calculation(user_id: str):
    """Verify hardcoded calculation against database"""
    try:
        result = point_calculator_integration.verify_calculation(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@point_calculator_bp.route('/api/points/calculator/gather-data/<user_id>', methods=['GET'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/gather-data/<user_id>', methods=['GET'])
@rate_limit()
def gather_data(user_id: str):
    """Gather point data from all systems (for debugging)"""
    try:
        data = point_calculator_integration.gather_point_data(user_id)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'point_data': data
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@point_calculator_bp.route('/api/points/calculator/test', methods=['GET'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/test', methods=['GET'])
@rate_limit()
def test_endpoint():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Point Calculator API is working!',
        'endpoints': {
            'calculate': '/api/points/calculator/calculate',
            'breakdown': '/api/points/calculator/breakdown/<user_id>',
            'verify': '/api/points/calculator/verify/<user_id>',
            'gather_data': '/api/points/calculator/gather-data/<user_id>',
            'predict': '/api/points/calculator/predict',
            'optimize': '/api/points/calculator/optimize',
            'multiplier-combinations': '/api/points/calculator/multiplier-combinations',
            'suggest-optimization': '/api/points/calculator/suggest-optimization'
        }
    }), 200

@point_calculator_bp.route('/api/points/calculator/predict', methods=['GET', 'POST'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/predict', methods=['GET', 'POST'])
@rate_limit()
def predict_points():
    """Predict future points based on activity patterns"""
    try:
        if request.method == 'GET':
            user_id = request.args.get('user_id') or get_user_id()
            activity_type = request.args.get('activity_type', 'general')
            base_points = float(request.args.get('base_points', 100))
            days = int(request.args.get('days', 7))
        else:
            data = InputValidator.get_json_safe(default={})
            user_id = data.get('user_id') or get_user_id()
            activity_type = data.get('activity_type', 'general')
            base_points = float(data.get('base_points', 100))
            days = int(data.get('days', 7))
        
        result = point_calculator_integration.predict_points(user_id, activity_type, base_points, days)
        # Ensure result has success key
        if not isinstance(result, dict):
            result = {'success': False, 'predictions': []}
        if 'success' not in result:
            result['success'] = True
        return jsonify(result), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error in point calculator predict: {e}", exc_info=True)
        # Return 200 with empty data instead of 500
        return jsonify({
            'success': False,
            'error': str(e),
            'predictions': [],
            'user_id': user_id,
            'activity_type': activity_type,
            'base_points': base_points,
            'days': days
        }), 200

@point_calculator_bp.route('/api/points/calculator/optimize', methods=['POST'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/optimize', methods=['POST'])
@rate_limit()
def optimize_multipliers():
    """Optimize multiplier combinations"""
    try:
        data = InputValidator.get_json_safe(default={})
        base_points = float(data.get('base_points', 100))
        available_multipliers = data.get('available_multipliers', {})
        target_points = data.get('target_points')
        
        if not available_multipliers:
            return jsonify({
                'success': False,
                'error': 'available_multipliers is required'
            }), 400
        
        result = point_calculator_integration.optimize_multipliers(
            base_points, available_multipliers, target_points
        )
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@point_calculator_bp.route('/api/points/calculator/multiplier-combinations', methods=['POST'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/multiplier-combinations', methods=['POST'])
@rate_limit()
def calculate_multiplier_combinations():
    """Calculate all possible multiplier combinations"""
    try:
        data = InputValidator.get_json_safe(default={})
        base_points = float(data.get('base_points', 100))
        multipliers = data.get('multipliers', {})
        
        if not multipliers:
            return jsonify({
                'success': False,
                'error': 'multipliers is required'
            }), 400
        
        result = point_calculator_integration.calculate_multiplier_combinations(base_points, multipliers)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@point_calculator_bp.route('/api/points/calculator/suggest-optimization', methods=['GET', 'POST'])
@point_calculator_bp.route('/vidgenerator/api/points/calculator/suggest-optimization', methods=['GET', 'POST'])
@rate_limit()
def suggest_optimization():
    """Get optimization suggestions for increasing points"""
    try:
        if request.method == 'GET':
            user_id = request.args.get('user_id') or get_user_id()
            current_points = float(request.args.get('current_points', 0))
            target_points = request.args.get('target_points')
        else:
            data = InputValidator.get_json_safe(default={})
            user_id = data.get('user_id') or get_user_id()
            current_points = float(data.get('current_points', 0))
            target_points = data.get('target_points')
        
        result = point_calculator_integration.suggest_optimization(
            user_id, current_points, float(target_points) if target_points else None
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
