"""
IP/MAC User Management Routes
API endpoints for IP/MAC-based user management
"""
from flask import Blueprint, request, jsonify, g
from backend.services.ip_mac_user_manager import ip_mac_user_manager
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

ip_mac_user_bp = Blueprint('ip_mac_user', __name__, url_prefix='')


@ip_mac_user_bp.route('/api/user/current', methods=['GET'])
@ip_mac_user_bp.route('/vidgenerator/api/user/current', methods=['GET'])
@rate_limit(endpoint='/api/user/current')
def get_current_user():
    """Get current user based on IP/MAC"""
    try:
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            # Fallback: get from IP
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) or 'unknown'
            mac_address = request.headers.get('X-Client-MAC') or request.headers.get('X-MAC-Address')
            user_agent = request.headers.get('User-Agent', 'unknown')
            
            user_info = ip_mac_user_manager.get_or_create_user(
                ip_address=ip_address,
                mac_address=mac_address,
                user_agent=user_agent
            )
            user_id = user_info['user_id']
        
        user_details = ip_mac_user_manager.get_user_details(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'user_details': user_details,
            'is_new': getattr(g, 'user_is_new', False)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@ip_mac_user_bp.route('/api/user/register-mac', methods=['POST'])
@ip_mac_user_bp.route('/vidgenerator/api/user/register-mac', methods=['POST'])
@rate_limit(endpoint='/api/user/register-mac')
def register_mac_address():
    """Register MAC address for current user"""
    try:
        data = InputValidator.get_json_safe(default={})
        mac_address = InputValidator.sanitize_string(data.get('mac_address', ''), max_length=50).strip()
        
        if not mac_address:
            return jsonify({
                'success': False,
                'error': 'MAC address is required'
            }), 400
        
        user_id = getattr(g, 'user_id', None)
        if not user_id:
            # Get from IP
            ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr) or 'unknown'
            user_info = ip_mac_user_manager.get_or_create_user(ip_address=ip_address)
            user_id = user_info['user_id']
        
        # Update user with MAC address
        ip_mac_user_manager.update_user_activity(user_id, mac_address=mac_address)
        
        return jsonify({
            'success': True,
            'message': 'MAC address registered',
            'user_id': user_id
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@ip_mac_user_bp.route('/api/user/statistics', methods=['GET'])
@ip_mac_user_bp.route('/vidgenerator/api/user/statistics', methods=['GET'])
@rate_limit(endpoint='/api/user/statistics')
def get_user_statistics():
    """Get user statistics"""
    try:
        stats = ip_mac_user_manager.get_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@ip_mac_user_bp.route('/api/user/list', methods=['GET'])
@ip_mac_user_bp.route('/vidgenerator/api/user/list', methods=['GET'])
@rate_limit(endpoint='/api/user/list')
def list_users():
    """List all users (admin function)"""
    try:
        users = ip_mac_user_manager.get_all_users()
        return jsonify({
            'success': True,
            'users': users,
            'count': len(users)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
