"""
Epic Gaming Experience Routes
Unified progression system that makes all activities count
"""
from flask import Blueprint, request, jsonify
from backend.services.epic_gaming_experience import epic_gaming_experience
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

epic_gaming_bp = Blueprint('epic_gaming', __name__)


@epic_gaming_bp.route('/api/game/epic/progress', methods=['GET'])
@epic_gaming_bp.route('/vidgenerator/api/game/epic/progress', methods=['GET'])
@rate_limit()
def get_epic_progress():
    """Get user's epic gaming progress"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        progress = epic_gaming_experience.get_user_progress(user_id)
        return jsonify(progress), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@epic_gaming_bp.route('/api/game/epic/track', methods=['POST'])
@epic_gaming_bp.route('/api/game/epic/track-activity', methods=['POST'])
@epic_gaming_bp.route('/vidgenerator/api/game/epic/track', methods=['POST'])
@epic_gaming_bp.route('/vidgenerator/api/game/epic/track-activity', methods=['POST'])
@rate_limit()
def track_activity():
    """Track an activity and award XP"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        activity_type = data.get('activity_type', 'unknown')
        metadata = data.get('metadata', {})
        
        if not activity_type or activity_type == 'unknown':
            return jsonify({
                'success': False,
                'error': 'activity_type is required'
            }), 400
        
        result = epic_gaming_experience.track_activity(user_id, activity_type, metadata)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@epic_gaming_bp.route('/api/game/epic/timeline', methods=['GET'])
@epic_gaming_bp.route('/vidgenerator/api/game/epic/timeline', methods=['GET'])
@rate_limit()
def get_timeline():
    """Get user's activity timeline"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 100))
        
        timeline = epic_gaming_experience.get_timeline(user_id, limit)
        return jsonify({
            'success': True,
            'timeline': timeline,
            'count': len(timeline)
        }), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@epic_gaming_bp.route('/api/game/epic/story', methods=['GET'])
@epic_gaming_bp.route('/vidgenerator/api/game/epic/story', methods=['GET'])
@rate_limit()
def get_story():
    """Get story progress"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        story = epic_gaming_experience.get_story(user_id)
        return jsonify({
            'success': True,
            **story
        }), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@epic_gaming_bp.route('/api/game/epic/level-info', methods=['GET'])
@epic_gaming_bp.route('/vidgenerator/api/game/epic/level-info', methods=['GET'])
@rate_limit()
def get_level_info():
    """Get detailed level information"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        progress = epic_gaming_experience.get_user_progress(user_id)
        
        return jsonify({
            'success': True,
            'level_info': progress['level_info'],
            'level_name': progress['level_name'],
            'total_xp': progress['total_xp']
        }), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)
