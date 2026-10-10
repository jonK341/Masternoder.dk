"""
Enhanced Profile Routes
Comprehensive profile API endpoints
"""
from flask import Blueprint, request, jsonify
from backend.services.profile_service import profile_service
from backend.services.avatar_service import avatar_service
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

profile_enhanced_bp = Blueprint('profile_enhanced', __name__, url_prefix='')


@profile_enhanced_bp.route('/api/profile/<user_id>', methods=['GET'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>', methods=['GET'])
@rate_limit(endpoint='/api/profile')
def get_profile(user_id: str):
    """Get comprehensive user profile"""
    try:
        profile = profile_service.get_comprehensive_profile(user_id)
        return jsonify({
            'success': True,
            'profile': profile
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>/summary', methods=['GET'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>/summary', methods=['GET'])
@rate_limit(endpoint='/api/profile/summary')
def get_profile_summary(user_id: str):
    """Get profile summary"""
    try:
        summary = profile_service.get_profile_summary(user_id)
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>/statistics', methods=['GET'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>/statistics', methods=['GET'])
@rate_limit(endpoint='/api/profile/statistics')
def get_profile_statistics(user_id: str):
    """Get profile statistics"""
    try:
        stats = profile_service.get_profile_statistics(user_id)
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>/timeline', methods=['GET'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>/timeline', methods=['GET'])
@rate_limit(endpoint='/api/profile/timeline')
def get_activity_timeline(user_id: str):
    """Get user activity timeline"""
    try:
        limit = max(1, min(100, int(request.args.get('limit', 50))))
        timeline = profile_service.get_activity_timeline(user_id, limit)
        
        return jsonify({
            'success': True,
            'timeline': timeline,
            'count': len(timeline)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>', methods=['PUT', 'PATCH'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>', methods=['PUT', 'PATCH'])
@rate_limit(endpoint='/api/profile/update')
def update_profile(user_id: str):
    """Update user profile"""
    try:
        data = InputValidator.get_json_safe(default={})
        
        # Allowed update fields
        allowed_fields = ['display_name', 'username', 'preferences', 'settings']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
        
        if not updates:
            return jsonify({
                'success': False,
                'error': 'No valid fields to update'
            }), 400
        
        updated_profile = profile_service.update_profile(user_id, updates)
        
        return jsonify({
            'success': True,
            'profile': updated_profile
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>/avatar', methods=['POST'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>/avatar', methods=['POST'])
@rate_limit(endpoint='/api/profile/avatar')
def upload_avatar(user_id: str):
    """Upload user avatar"""
    try:
        # Check if file upload or base64
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'success': False,
                    'error': 'No file selected'
                }), 400
            
            file_data = file.read()
            result = avatar_service.upload_avatar(user_id, file_data, file.filename)
            
        elif 'avatar' in request.json:
            # Base64 upload
            base64_data = request.json.get('avatar')
            result = avatar_service.upload_avatar_base64(user_id, base64_data)
        else:
            return jsonify({
                'success': False,
                'error': 'No file or avatar data provided'
            }), 400
        
        return jsonify(result), 200 if result.get('success') else 400
        
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>/avatar', methods=['DELETE'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>/avatar', methods=['DELETE'])
@rate_limit(endpoint='/api/profile/avatar/delete')
def delete_avatar(user_id: str):
    """Delete user avatar"""
    try:
        result = avatar_service.delete_avatar(user_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@profile_enhanced_bp.route('/api/profile/<user_id>/avatar', methods=['GET'])
@profile_enhanced_bp.route('/vidgenerator/api/profile/<user_id>/avatar', methods=['GET'])
@rate_limit(endpoint='/api/profile/avatar/get')
def get_avatar(user_id: str):
    """Get user avatar URL"""
    try:
        size = request.args.get('size', 'medium')
        avatar_url = avatar_service.get_avatar_url(user_id, size)
        
        return jsonify({
            'success': True,
            'avatar_url': avatar_url,
            'size': size
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
