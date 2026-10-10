"""
Points API - Graduation Points and Chat Points
"""

from flask import Blueprint, request, jsonify
from typing import Dict, Any

points_api_bp = Blueprint('points_api', __name__)

# Import points systems
try:
    from src.services.behavioral_tracking.graduation_points import graduation_points_system
except ImportError:
    graduation_points_system = None

try:
    from src.services.behavioral_tracking.chat_points import chat_points_system
except ImportError:
    chat_points_system = None

try:
    from src.services.behavioral_tracking.generation_tracker import get_user_id_from_request
except ImportError:
    def get_user_id_from_request(request):
        return request.remote_addr or "user_anonymous"


@points_api_bp.route('/api/points/graduation', methods=['GET'])
def get_graduation_points():
    """Get user's graduation points and milestones"""
    try:
        user_id = get_user_id_from_request(request)
        
        if not graduation_points_system:
            return jsonify({
                'success': False,
                'error': 'Graduation points system not available'
            }), 500
        
        points_data = graduation_points_system.get_graduation_points(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            **points_data
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@points_api_bp.route('/api/points/chat', methods=['GET'])
def get_chat_points():
    """Get user's chat points and stats"""
    try:
        user_id = get_user_id_from_request(request)
        
        if not chat_points_system:
            return jsonify({
                'success': False,
                'error': 'Chat points system not available'
            }), 500
        
        chat_data = chat_points_system.get_chat_points(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            **chat_data
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@points_api_bp.route('/api/points/chat/award', methods=['POST'])
def award_chat_points():
    """Award chat points for sending a message"""
    try:
        user_id = get_user_id_from_request(request)
        data = request.get_json() or {}
        
        if not chat_points_system:
            return jsonify({
                'success': False,
                'error': 'Chat points system not available'
            }), 500
        
        action_type = data.get('action_type', 'send_message')
        message_length = data.get('message_length', 0)
        metadata = data.get('metadata', {})
        
        result = chat_points_system.award_chat_points(
            user_id=user_id,
            action_type=action_type,
            message_length=message_length,
            metadata=metadata
        )
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            **result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@points_api_bp.route('/api/points/all', methods=['GET'])
def get_all_points():
    """Get all points (graduation + chat) for user"""
    try:
        user_id = get_user_id_from_request(request)
        
        result = {
            'success': True,
            'user_id': user_id,
            'graduation_points': {},
            'chat_points': {}
        }
        
        if graduation_points_system:
            result['graduation_points'] = graduation_points_system.get_graduation_points(user_id)
        
        if chat_points_system:
            result['chat_points'] = chat_points_system.get_chat_points(user_id)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

