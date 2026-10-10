"""
Spectator Routes
API endpoints for spectator system
"""
from flask import Blueprint, request, jsonify
from backend.services.spectator_system import spectator_system
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

spectator_bp = Blueprint('spectator', __name__, url_prefix='')


@spectator_bp.route('/api/battle/spectator/join', methods=['POST'])
@spectator_bp.route('/vidgenerator/api/battle/spectator/join', methods=['POST'])
@rate_limit(endpoint='/api/battle/spectator/join')
def join_spectator():
    """Join spectator queue for a battle"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        battle_id = InputValidator.sanitize_string(data.get('battle_id', ''), max_length=100).strip()
        
        if not battle_id:
            return jsonify({
                'success': False,
                'error': 'battle_id is required'
            }), 400
        
        result = spectator_system.join_spectator_queue(user_id, battle_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@spectator_bp.route('/api/battle/spectator/leave', methods=['POST'])
@spectator_bp.route('/vidgenerator/api/battle/spectator/leave', methods=['POST'])
@rate_limit(endpoint='/api/battle/spectator/leave')
def leave_spectator():
    """Leave spectator mode"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        
        result = spectator_system.leave_spectator(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@spectator_bp.route('/api/battle/spectator/battles', methods=['GET'])
@spectator_bp.route('/vidgenerator/api/battle/spectator/battles', methods=['GET'])
@rate_limit(endpoint='/api/battle/spectator/battles')
def get_spectatable_battles():
    """Get list of battles that can be spectated"""
    try:
        limit = max(1, min(100, int(request.args.get('limit', 20))))
        battles = spectator_system.get_spectatable_battles(limit)
        
        return jsonify({
            'success': True,
            'battles': battles,
            'count': len(battles)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@spectator_bp.route('/api/battle/spectator/<battle_id>/count', methods=['GET'])
@spectator_bp.route('/vidgenerator/api/battle/spectator/<battle_id>/count', methods=['GET'])
@rate_limit(endpoint='/api/battle/spectator/count')
def get_spectator_count(battle_id: str):
    """Get number of spectators for a battle"""
    try:
        count = spectator_system.get_spectator_count(battle_id)
        spectators = spectator_system.get_spectators(battle_id)
        
        return jsonify({
            'success': True,
            'battle_id': battle_id,
            'spectator_count': count,
            'spectators': spectators
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@spectator_bp.route('/api/battle/spectator/activity', methods=['POST'])
@spectator_bp.route('/vidgenerator/api/battle/spectator/activity', methods=['POST'])
@rate_limit(endpoint='/api/battle/spectator/activity')
def update_spectator_activity():
    """Update spectator activity (heartbeat)"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        
        spectator_system.update_spectator_activity(user_id)
        
        return jsonify({
            'success': True,
            'message': 'Activity updated'
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
