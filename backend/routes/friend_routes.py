"""
Friend Routes
API endpoints for friend system
"""
from flask import Blueprint, request, jsonify
from backend.services.friend_system import friend_system
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

friend_bp = Blueprint('friend', __name__, url_prefix='')


@friend_bp.route('/api/friends/request', methods=['POST'])
@friend_bp.route('/vidgenerator/api/friends/request', methods=['POST'])
@rate_limit(endpoint='/api/friends/request')
def send_friend_request():
    """Send a friend request"""
    try:
        data = InputValidator.get_json_safe(default={})
        from_user_id = InputValidator.sanitize_string(data.get('from_user_id', 'default_user'), max_length=100).strip()
        to_user_id = InputValidator.sanitize_string(data.get('to_user_id', ''), max_length=100).strip()
        message = InputValidator.sanitize_string(data.get('message', ''), max_length=500).strip()
        
        if not to_user_id:
            return jsonify({
                'success': False,
                'error': 'to_user_id is required'
            }), 400
        
        result = friend_system.send_friend_request(from_user_id, to_user_id, message)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@friend_bp.route('/api/friends/accept', methods=['POST'])
@friend_bp.route('/vidgenerator/api/friends/accept', methods=['POST'])
@rate_limit(endpoint='/api/friends/accept')
def accept_friend_request():
    """Accept a friend request"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        from_user_id = InputValidator.sanitize_string(data.get('from_user_id', ''), max_length=100).strip()
        
        if not from_user_id:
            return jsonify({
                'success': False,
                'error': 'from_user_id is required'
            }), 400
        
        result = friend_system.accept_friend_request(user_id, from_user_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@friend_bp.route('/api/friends/reject', methods=['POST'])
@friend_bp.route('/vidgenerator/api/friends/reject', methods=['POST'])
@rate_limit(endpoint='/api/friends/reject')
def reject_friend_request():
    """Reject a friend request"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        from_user_id = InputValidator.sanitize_string(data.get('from_user_id', ''), max_length=100).strip()
        
        if not from_user_id:
            return jsonify({
                'success': False,
                'error': 'from_user_id is required'
            }), 400
        
        result = friend_system.reject_friend_request(user_id, from_user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@friend_bp.route('/api/friends/list/<user_id>', methods=['GET'])
@friend_bp.route('/vidgenerator/api/friends/list/<user_id>', methods=['GET'])
@rate_limit(endpoint='/api/friends/list')
def get_friends(user_id: str):
    """Get user's friends list"""
    try:
        friends = friend_system.get_friends(user_id)
        return jsonify({
            'success': True,
            'friends': friends,
            'count': len(friends)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@friend_bp.route('/api/friends/requests/<user_id>', methods=['GET'])
@friend_bp.route('/vidgenerator/api/friends/requests/<user_id>', methods=['GET'])
@rate_limit(endpoint='/api/friends/requests')
def get_friend_requests(user_id: str):
    """Get pending friend requests"""
    try:
        requests = friend_system.get_friend_requests(user_id)
        return jsonify({
            'success': True,
            'requests': requests,
            'count': len(requests)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@friend_bp.route('/api/friends/remove', methods=['POST'])
@friend_bp.route('/vidgenerator/api/friends/remove', methods=['POST'])
@rate_limit(endpoint='/api/friends/remove')
def remove_friend():
    """Remove a friend"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100).strip()
        friend_id = InputValidator.sanitize_string(data.get('friend_id', ''), max_length=100).strip()
        
        if not friend_id:
            return jsonify({
                'success': False,
                'error': 'friend_id is required'
            }), 400
        
        result = friend_system.remove_friend(user_id, friend_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@friend_bp.route('/api/friends/activity/<user_id>', methods=['GET'])
@friend_bp.route('/vidgenerator/api/friends/activity/<user_id>', methods=['GET'])
@rate_limit(endpoint='/api/friends/activity')
def get_friend_activity(user_id: str):
    """Get friend activity feed"""
    try:
        limit = max(1, min(100, int(request.args.get('limit', 20))))
        activity = friend_system.get_friend_activity(user_id, limit)
        
        return jsonify({
            'success': True,
            'activity': activity,
            'count': len(activity)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
