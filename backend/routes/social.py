"""
Social Network API Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.social_network import social_network
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import sys
import uuid

social_bp = Blueprint('social', __name__)

@social_bp.route('/api/social/friends/add', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/friends/add', methods=['POST'])
@rate_limit(endpoint='/api/social/friends/add')
def add_friend():
    """Add a friend"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['friend_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        friend_id = InputValidator.sanitize_string(data.get('friend_id', ''), max_length=50).strip()
        
        result = social_network.add_friend(user_id, friend_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/friends/remove', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/friends/remove', methods=['POST'])
@rate_limit(endpoint='/api/social/friends/remove')
def remove_friend():
    """Remove a friend"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['friend_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        friend_id = InputValidator.sanitize_string(data.get('friend_id', ''), max_length=50).strip()
        
        result = social_network.remove_friend(user_id, friend_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/follow', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/follow', methods=['POST'])
@rate_limit(endpoint='/api/social/follow')
def follow_user():
    """Follow a user"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['follow_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        follow_id = InputValidator.sanitize_string(data.get('follow_id', ''), max_length=50).strip()
        
        result = social_network.follow_user(user_id, follow_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/posts', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/posts', methods=['POST'])
@rate_limit(endpoint='/api/social/posts')
def create_post():
    """Create a post"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['content'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        content = InputValidator.sanitize_string(data.get('content', ''), max_length=5000).strip()
        post_type = InputValidator.sanitize_string(data.get('post_type', 'text'), max_length=20).strip()
        media_url = InputValidator.sanitize_string(data.get('media_url', ''), max_length=500).strip() if data.get('media_url') else None
        
        # Validate content length
        if not InputValidator.validate_length(content, min_length=1, max_length=5000):
            return jsonify({
                'success': False,
                'error': 'content must be between 1 and 5000 characters'
            }), 400
        
        result = social_network.create_post(user_id, content, post_type, media_url)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/posts/<post_id>/like', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/posts/<post_id>/like', methods=['POST'])
@rate_limit(endpoint='/api/social/posts/like')
def like_post(post_id):
    """Like a post"""
    try:
        # Sanitize post_id from URL
        post_id = InputValidator.sanitize_string(post_id, max_length=50).strip()
        
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        
        result = social_network.like_post(post_id, user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/posts/<post_id>/comment', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/posts/<post_id>/comment', methods=['POST'])
@rate_limit(endpoint='/api/social/posts/comment')
def comment_post(post_id):
    """Comment on a post"""
    try:
        # Sanitize post_id from URL
        post_id = InputValidator.sanitize_string(post_id, max_length=50).strip()
        
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['comment'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        comment = InputValidator.sanitize_string(data.get('comment', ''), max_length=2000).strip()
        
        # Validate comment length
        if not InputValidator.validate_length(comment, min_length=1, max_length=2000):
            return jsonify({
                'success': False,
                'error': 'comment must be between 1 and 2000 characters'
            }), 400
        
        result = social_network.comment_post(post_id, user_id, comment)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/posts/<post_id>/media', methods=['POST'])
@social_bp.route('/vidgenerator/api/social/posts/<post_id>/media', methods=['POST'])
@rate_limit(endpoint='/api/social/posts/media')
def upload_post_media(post_id):
    """Upload media to a post"""
    try:
        post_id = InputValidator.sanitize_string(post_id, max_length=50).strip()
        user_id = InputValidator.sanitize_string(request.form.get('user_id', 'default_user'), max_length=50).strip()
        
        if 'media' not in request.files:
            return jsonify({'success': False, 'error': 'No media file provided'}), 400
        
        file = request.files['media']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'mp4', 'mov', 'webm'}
        if '.' in file.filename:
            ext = file.filename.rsplit('.', 1)[1].lower()
            if ext not in allowed_extensions:
                return jsonify({'success': False, 'error': f'File type .{ext} not allowed'}), 400
        
        import os
        from datetime import datetime
        upload_dir = os.path.join('vidgenerator', 'static', 'uploads', 'posts')
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = f"{post_id}_{datetime.utcnow().timestamp()}_{file.filename}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        media_url = f"/vidgenerator/static/uploads/posts/{filename}"
        result = social_network.add_media_to_post(post_id, user_id, media_url)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@social_bp.route('/api/social/posts/<post_id>/comments', methods=['GET'])
@social_bp.route('/vidgenerator/api/social/posts/<post_id>/comments', methods=['GET'])
@rate_limit(endpoint='/api/social/posts/comments')
def get_post_comments(post_id):
    """Get comments for a post"""
    try:
        post_id = InputValidator.sanitize_string(post_id, max_length=50).strip()
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        
        comments = social_network.comments.get(post_id, [])
        paginated_comments = comments[offset:offset + limit]
        
        return jsonify({
            'success': True,
            'post_id': post_id,
            'comments': paginated_comments,
            'total': len(comments),
            'limit': limit,
            'offset': offset
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@social_bp.route('/api/social/posts/<post_id>', methods=['DELETE'])
@social_bp.route('/vidgenerator/api/social/posts/<post_id>', methods=['DELETE'])
@rate_limit(endpoint='/api/social/posts/delete')
def delete_post(post_id):
    """Delete a post"""
    try:
        post_id = InputValidator.sanitize_string(post_id, max_length=50).strip()
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'), max_length=50).strip()
        
        posts = social_network.posts
        post = next((p for p in posts if p.get('id') == post_id), None)
        
        if not post:
            return jsonify({'success': False, 'error': 'Post not found'}), 404
        
        if post.get('user_id') != user_id:
            return jsonify({'success': False, 'error': 'You can only delete your own posts'}), 403
        
        posts.remove(post)
        if post_id in social_network.likes:
            del social_network.likes[post_id]
        if post_id in social_network.comments:
            del social_network.comments[post_id]
        
        return jsonify({'success': True, 'message': 'Post deleted successfully'}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@social_bp.route('/api/social/feed', methods=['GET'])
@social_bp.route('/vidgenerator/api/social/feed', methods=['GET'])
def get_feed():
    """Get social feed"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 20))
        
        feed_data = social_network.get_feed(user_id, limit)
        social_data = {
            'success': True,
            'feed': feed_data
        }
        
        # Enhance social data with future tech
        try:
            from backend.services.future_tech_integration_service import future_tech_integration_service
            social_data = future_tech_integration_service.enhance_social_data(user_id, social_data)
        except Exception as e:
            print(f"[Social] Error enhancing social data: {e}")
        
        return jsonify(social_data), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/friends', methods=['GET'])
@social_bp.route('/vidgenerator/api/social/friends', methods=['GET'])
def get_friends():
    """Get friends list"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        friends_data = social_network.get_friends(user_id)
        social_data = {
            'success': True,
            'friends': friends_data
        }
        
        # Enhance social data with future tech
        try:
            from backend.services.future_tech_integration_service import future_tech_integration_service
            social_data = future_tech_integration_service.enhance_social_data(user_id, social_data)
        except Exception as e:
            print(f"[Social] Error enhancing social data: {e}")
        
        return jsonify(social_data), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/followers', methods=['GET'])
@social_bp.route('/vidgenerator/api/social/followers', methods=['GET'])
def get_followers():
    """Get followers list"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        followers = social_network.get_followers(user_id)
        return jsonify({
            'success': True,
            'followers': followers
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@social_bp.route('/api/social/following', methods=['GET'])
@social_bp.route('/vidgenerator/api/social/following', methods=['GET'])
def get_following():
    """Get following list"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        following = social_network.get_following(user_id)
        return jsonify({
            'success': True,
            'following': following
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

