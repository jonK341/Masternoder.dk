"""
Guild Routes
API endpoints for guild/clan system
"""
from flask import Blueprint, request, jsonify
from backend.services.guild_system import guild_system
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

guild_bp = Blueprint('guild', __name__, url_prefix='')


@guild_bp.route('/api/guild/create', methods=['POST'])
@guild_bp.route('/vidgenerator/api/guild/create', methods=['POST'])
@rate_limit(endpoint='/api/guild/create')
def create_guild():
    """Create a new guild"""
    try:
        data = InputValidator.get_json_safe(default={})
        creator_id = InputValidator.sanitize_string(data.get('creator_id', 'default_user'), max_length=100).strip()
        name = InputValidator.sanitize_string(data.get('name', ''), max_length=50).strip()
        description = InputValidator.sanitize_string(data.get('description', ''), max_length=500).strip()
        tag = InputValidator.sanitize_string(data.get('tag', ''), max_length=10).strip()
        privacy = InputValidator.sanitize_string(data.get('privacy', 'public'), max_length=20).strip()
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'Guild name is required'
            }), 400
        
        result = guild_system.create_guild(creator_id, name, description, tag, privacy)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@guild_bp.route('/api/guild/join', methods=['POST'])
@guild_bp.route('/vidgenerator/api/guild/join', methods=['POST'])
@rate_limit(endpoint='/api/guild/join')
def join_guild():
    """Join a guild"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        guild_id = InputValidator.sanitize_string(data.get('guild_id', ''), max_length=100).strip()
        
        if not guild_id:
            return jsonify({
                'success': False,
                'error': 'guild_id is required'
            }), 400
        
        result = guild_system.join_guild(user_id, guild_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@guild_bp.route('/api/guild/leave', methods=['POST'])
@guild_bp.route('/vidgenerator/api/guild/leave', methods=['POST'])
@rate_limit(endpoint='/api/guild/leave')
def leave_guild():
    """Leave current guild"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        
        result = guild_system.leave_guild(user_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@guild_bp.route('/api/guild/<guild_id>', methods=['GET'])
@guild_bp.route('/vidgenerator/api/guild/<guild_id>', methods=['GET'])
@rate_limit(endpoint='/api/guild/get')
def get_guild(guild_id: str):
    """Get guild information"""
    try:
        guild = guild_system.get_guild(guild_id)
        if not guild:
            return jsonify({
                'success': False,
                'error': 'Guild not found'
            }), 404
        
        members = guild_system.get_guild_members(guild_id)
        
        return jsonify({
            'success': True,
            'guild': guild,
            'members': members
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@guild_bp.route('/api/guild/user/<user_id>', methods=['GET'])
@guild_bp.route('/vidgenerator/api/guild/user/<user_id>', methods=['GET'])
@rate_limit(endpoint='/api/guild/user')
def get_user_guild(user_id: str):
    """Get user's current guild"""
    try:
        guild = guild_system.get_user_guild(user_id)
        if not guild:
            return jsonify({
                'success': True,
                'guild': None,
                'message': 'User not in a guild'
            }), 200
        
        guild_id = guild['guild_id']
        members = guild_system.get_guild_members(guild_id)
        
        return jsonify({
            'success': True,
            'guild': guild,
            'members': members
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@guild_bp.route('/api/guild/leaderboard', methods=['GET'])
@guild_bp.route('/vidgenerator/api/guild/leaderboard', methods=['GET'])
@rate_limit(endpoint='/api/guild/leaderboard')
def get_guild_leaderboard():
    """Get guild leaderboard"""
    try:
        limit = max(1, min(100, int(request.args.get('limit', 20))))
        leaderboard = guild_system.get_guild_leaderboard(limit)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'count': len(leaderboard)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
