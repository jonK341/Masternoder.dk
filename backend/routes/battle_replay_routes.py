"""
Battle Replay Routes
API endpoints for battle replay system
"""
from flask import Blueprint, request, jsonify
from backend.services.battle_replay_system import battle_replay_system
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

battle_replay_bp = Blueprint('battle_replay', __name__, url_prefix='')


@battle_replay_bp.route('/api/battle/replay/record', methods=['POST'])
@battle_replay_bp.route('/vidgenerator/api/battle/replay/record', methods=['POST'])
@rate_limit(endpoint='/api/battle/replay/record')
def record_battle():
    """Record a battle for replay"""
    try:
        data = InputValidator.get_json_safe(default={})
        battle_id = InputValidator.sanitize_string(data.get('battle_id', ''), max_length=100).strip()
        battle_data = data.get('battle_data', {})
        actions = data.get('actions', [])
        
        if not battle_id:
            return jsonify({
                'success': False,
                'error': 'battle_id is required'
            }), 400
        
        result = battle_replay_system.record_battle(battle_id, battle_data, actions)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_replay_bp.route('/api/battle/replay/<replay_id>', methods=['GET'])
@battle_replay_bp.route('/vidgenerator/api/battle/replay/<replay_id>', methods=['GET'])
@rate_limit(endpoint='/api/battle/replay')
def get_replay(replay_id: str):
    """Get replay data"""
    try:
        replay = battle_replay_system.get_replay(replay_id)
        if not replay:
            return jsonify({
                'success': False,
                'error': 'Replay not found'
            }), 404
        
        return jsonify({
            'success': True,
            'replay': replay
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_replay_bp.route('/api/battle/replay/user/<user_id>', methods=['GET'])
@battle_replay_bp.route('/vidgenerator/api/battle/replay/user/<user_id>', methods=['GET'])
@rate_limit(endpoint='/api/battle/replay/user')
def get_user_replays(user_id: str):
    """Get all replays for a user"""
    try:
        limit = max(1, min(100, int(request.args.get('limit', 50))))
        replays = battle_replay_system.get_user_replays(user_id, limit)
        
        return jsonify({
            'success': True,
            'replays': replays,
            'count': len(replays)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_replay_bp.route('/api/battle/replay/share/<replay_id>', methods=['POST'])
@battle_replay_bp.route('/vidgenerator/api/battle/replay/share/<replay_id>', methods=['POST'])
@rate_limit(endpoint='/api/battle/replay/share')
def share_replay(replay_id: str):
    """Generate shareable link for replay"""
    try:
        data = InputValidator.get_json_safe(default={})
        share_token = InputValidator.sanitize_string(data.get('share_token', ''), max_length=50).strip() or None
        
        result = battle_replay_system.share_replay(replay_id, share_token)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_replay_bp.route('/api/battle/replay/<replay_id>', methods=['DELETE'])
@battle_replay_bp.route('/vidgenerator/api/battle/replay/<replay_id>', methods=['DELETE'])
@rate_limit(endpoint='/api/battle/replay/delete')
def delete_replay(replay_id: str):
    """Delete a replay"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = battle_replay_system.delete_replay(replay_id, user_id)
        
        if not result.get('success'):
            return jsonify(result), 403
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
