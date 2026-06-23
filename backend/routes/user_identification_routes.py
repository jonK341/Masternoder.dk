"""
User Identification Routes
API endpoints for user identification and creation
"""
from flask import Blueprint, jsonify, request
from backend.services.user_identification import user_identification


# Lazy proxy: defer importing the user_onboarding singleton until first use so a
# startup-time circular import can't block this blueprint from registering.
class _LazyUserOnboarding:
    def __getattr__(self, name):
        from backend.services.user_onboarding import user_onboarding as _uo
        return getattr(_uo, name)


user_onboarding = _LazyUserOnboarding()

user_identification_bp = Blueprint('user_identification', __name__)

@user_identification_bp.route('/api/user/identify', methods=['POST'])
def identify_user():
    """Identify or create user based on request data"""
    try:
        # Get request data
        request_data = request.get_json() or {}
        
        # Add request headers to data
        request_data.update({
            'user_agent': request.headers.get('User-Agent', ''),
            'ip_address': request.remote_addr,
            'language': request.headers.get('Accept-Language', ''),
            'referral_source': request.headers.get('Referer', '') or 'direct'
        })
        
        # Identify or create user
        result = user_identification.identify_or_create_user(request)
        
        if result.get('success'):
            user_id = result.get('user_id')
            
            # If new user, create profile
            if result.get('new_user'):
                try:
                    create_result = user_onboarding.create_new_user(request_data, user_id)
                    if create_result.get('success'):
                        result['profile_created'] = True
                except Exception as e:
                    # Don't fail if profile creation fails
                    result['profile_created'] = False
                    result['profile_error'] = str(e)
            
            return jsonify(result), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to identify user'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_identification_bp.route('/api/user/identify/simple', methods=['GET', 'POST'])
def identify_user_simple():
    """Simple user identification - returns user ID"""
    try:
        # Identify or create user
        result = user_identification.identify_or_create_user(request)
        
        if result.get('success'):
            user_id = result.get('user_id')
            
            # If new user, create basic profile
            if result.get('new_user'):
                try:
                    request_data = {
                        'user_agent': request.headers.get('User-Agent', ''),
                        'ip_address': request.remote_addr,
                        'language': request.headers.get('Accept-Language', ''),
                        'referral_source': 'direct'
                    }
                    user_onboarding.create_new_user(request_data, user_id)
                except:
                    pass  # Don't fail if profile creation fails
            
            return jsonify({
                'success': True,
                'user_id': user_id,
                'new_user': result.get('new_user', False)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to identify user',
                'user_id': 'default_user'  # Fallback only if identification fails
            }), 200  # Return 200 with fallback instead of error
            
    except Exception as e:
        # Return default_user as fallback on error
        return jsonify({
            'success': False,
            'error': str(e),
            'user_id': 'default_user'
        }), 200
