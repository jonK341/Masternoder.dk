"""
Player Profiler API Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.player_profiler import player_profiler
import sys

profiler_bp = Blueprint('profiler', __name__)

@profiler_bp.route('/api/profiler/profile', methods=['GET'])
@profiler_bp.route('/vidgenerator/api/profiler/profile', methods=['GET'])
def get_profile():
    """Get player profile"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        profile = player_profiler.get_profile(user_id)
        pictures = player_profiler.get_picture_features(user_id)
        return jsonify({
            'success': True,
            'profile': profile,
            'pictures': pictures,
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@profiler_bp.route('/api/profiler/update', methods=['POST'])
@profiler_bp.route('/vidgenerator/api/profiler/update', methods=['POST'])
def update_profile():
    """Update player profile"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        stats = data.get('stats', {})
        action_type = data.get('action_type', 'general')
        
        result = player_profiler.update_profile(user_id, stats, action_type)
        return jsonify({
            'success': True,
            **result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@profiler_bp.route('/api/profiler/track', methods=['POST'])
@profiler_bp.route('/vidgenerator/api/profiler/track', methods=['POST'])
def track_action():
    """Track a player action"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        action_type = data.get('action_type')
        metadata = data.get('metadata', {})
        
        if not action_type:
            return jsonify({
                'success': False,
                'error': 'action_type is required'
            }), 400
        
        result = player_profiler.track_action(user_id, action_type, metadata)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@profiler_bp.route('/api/profiler/triggers', methods=['GET'])
@profiler_bp.route('/vidgenerator/api/profiler/triggers', methods=['GET'])
def get_triggers():
    """Get available triggers"""
    try:
        triggers = list(player_profiler.triggers.values())
        return jsonify({
            'success': True,
            'triggers': triggers
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@profiler_bp.route('/api/profiler/history', methods=['GET'])
@profiler_bp.route('/vidgenerator/api/profiler/history', methods=['GET'])
def get_trigger_history():
    """Get trigger history"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 10))
        
        history = player_profiler.get_trigger_history(user_id, limit)
        return jsonify({
            'success': True,
            'history': history
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@profiler_bp.route('/api/profiler/pictures', methods=['GET'])
@profiler_bp.route('/vidgenerator/api/profiler/pictures', methods=['GET'])
def get_pictures():
    """Saved avatar + gallery plus camgirl studio portrait board."""
    try:
        user_id = request.args.get('user_id', 'default_user')
        payload = player_profiler.get_picture_features(user_id)
        return jsonify({'success': True, **payload}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@profiler_bp.route('/api/profiler/pictures', methods=['POST'])
@profiler_bp.route('/vidgenerator/api/profiler/pictures', methods=['POST'])
def add_picture():
    """Save a picture URL to the player gallery."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        url = data.get('url') or data.get('picture_url')
        source = data.get('source') or 'manual'
        result = player_profiler.add_picture(user_id, url, source=source)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@profiler_bp.route('/api/profiler/pictures/avatar', methods=['POST'])
@profiler_bp.route('/vidgenerator/api/profiler/pictures/avatar', methods=['POST'])
def set_profiler_avatar():
    """Set profiler avatar from a picture URL."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        url = data.get('url') or data.get('avatar_url')
        result = player_profiler.set_avatar_url(user_id, url)
        status = 200 if result.get('success') else 400
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

