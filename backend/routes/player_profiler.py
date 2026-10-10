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
        return jsonify({
            'success': True,
            'profile': profile
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

