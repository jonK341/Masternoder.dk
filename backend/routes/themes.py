"""
Themes Routes - Manage video generation themes
"""
from flask import Blueprint, request, jsonify
from backend.services.themes_system import themes_system
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

themes_bp = Blueprint('themes', __name__)


@themes_bp.route('/api/themes/list', methods=['GET'])
def list_themes():
    """Get all available themes"""
    try:
        category = request.args.get('category')
        
        if category:
            themes = themes_system.get_themes_by_category(category)
        else:
            themes = themes_system.get_all_themes()
        
        return jsonify({
            'success': True,
            'themes': themes,
            'total': len(themes)
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@themes_bp.route('/api/themes/<theme_id>', methods=['GET'])
def get_theme(theme_id: str):
    """Get specific theme"""
    try:
        theme = themes_system.get_theme(theme_id)
        
        if not theme:
            return jsonify({
                'success': False,
                'error': 'Theme not found'
            }), 404
        
        return jsonify({
            'success': True,
            'theme': theme
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@themes_bp.route('/api/themes/unlock', methods=['POST'])
@rate_limit
def unlock_theme():
    """Unlock theme for user"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        theme_id = InputValidator.sanitize_string(data.get('theme_id', ''))
        
        result = themes_system.unlock_theme(user_id, theme_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@themes_bp.route('/api/themes/use', methods=['POST'])
@rate_limit
def use_theme():
    """Record theme usage"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        theme_id = InputValidator.sanitize_string(data.get('theme_id', ''))
        
        result = themes_system.use_theme(user_id, theme_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@themes_bp.route('/api/themes/user', methods=['GET'])
def get_user_themes():
    """Get themes unlocked by user"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        themes = themes_system.get_user_themes(user_id)
        return jsonify(themes), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@themes_bp.route('/api/themes/stats', methods=['GET'])
def get_theme_stats():
    """Get theme statistics for user"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        theme_id = request.args.get('theme_id')
        
        if theme_id:
            stats = themes_system.get_theme_stats(user_id, theme_id)
        else:
            themes = themes_system.get_user_themes(user_id)
            stats = {
                'success': True,
                'themes': themes.get('themes', []),
                'stats': themes.get('stats', {})
            }
        
        return jsonify(stats), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

