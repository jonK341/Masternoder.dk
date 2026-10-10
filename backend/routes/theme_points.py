"""
Theme Points Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.theme_points_system import theme_points_system
from backend.utils.input_validator import InputValidator
from backend.utils.error_handler import ErrorHandler
from backend.utils.rate_limiter import rate_limit

theme_points_bp = Blueprint('theme_points', __name__)


@theme_points_bp.route('/api/theme-points/award', methods=['POST'])
@rate_limit
def award_theme_points():
    """Award theme points to user"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        theme = InputValidator.sanitize_string(data.get('theme'))
        points = int(data.get('points', 0))
        source = InputValidator.sanitize_string(data.get('source', 'general'))
        
        if not theme:
            return ErrorHandler.create_error_response('theme required', 400)
        
        result = theme_points_system.award_theme_points(user_id, theme, points, source)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@theme_points_bp.route('/api/theme-points/user', methods=['GET'])
@rate_limit
def get_user_theme_points():
    """Get user theme points"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        result = theme_points_system.get_user_theme_points(user_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@theme_points_bp.route('/api/theme-points/leaderboard/<theme>', methods=['GET'])
@rate_limit
def get_theme_leaderboard(theme: str):
    """Get theme leaderboard"""
    try:
        limit = int(request.args.get('limit', 10))
        
        result = theme_points_system.get_theme_leaderboard(theme, limit)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@theme_points_bp.route('/api/theme-points/stats', methods=['GET'])
@rate_limit
def get_all_theme_stats():
    """Get all theme stats"""
    try:
        result = theme_points_system.get_all_theme_stats()
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

