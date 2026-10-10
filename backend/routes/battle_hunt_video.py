"""
Battle & Hunt Video Integration Routes
API endpoints for generating videos from battle and hunt events
"""
from flask import Blueprint, request, jsonify, current_app
from backend.services.battle_hunt_video_integration import battle_hunt_video_integration
from backend.utils.input_validator import InputValidator
from backend.utils.error_handler import ErrorHandler
from backend.utils.rate_limiter import rate_limit
import threading

battle_hunt_video_bp = Blueprint('battle_hunt_video', __name__)


@battle_hunt_video_bp.route('/api/battle-hunt-video/battle/generate', methods=['POST'])
@rate_limit
def generate_battle_video():
    """Generate a video from battle results"""
    try:
        data = InputValidator.get_json_safe(request)
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['battle_id', 'battle_result'])
        if not is_valid:
            return ErrorHandler.create_error_response(error_msg, 400)
        
        battle_id = InputValidator.sanitize_string(data.get('battle_id'))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        battle_result = data.get('battle_result', {})
        video_style = InputValidator.sanitize_string(data.get('video_style', 'epic'))
        quality = InputValidator.sanitize_string(data.get('quality', 'medium'))
        
        # Validate video_style
        if video_style not in ['epic', 'cinematic', 'action', 'documentary']:
            video_style = 'epic'
        
        # Validate quality
        if quality not in ['low', 'medium', 'high']:
            quality = 'medium'
        
        # Generate video (can be async)
        async_mode = data.get('async', False)
        
        if async_mode:
            # Generate in background thread
            app = current_app._get_current_object()
            def generate_async():
                with app.app_context():
                    battle_hunt_video_integration.generate_battle_video(
                        battle_id=battle_id,
                        user_id=user_id,
                        battle_result=battle_result,
                        video_style=video_style,
                        quality=quality
                    )
            
            thread = threading.Thread(target=generate_async)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "message": "Video generation started in background",
                "battle_id": battle_id,
                "status": "processing"
            }), 202
        else:
            # Generate synchronously
            result = battle_hunt_video_integration.generate_battle_video(
                battle_id=battle_id,
                user_id=user_id,
                battle_result=battle_result,
                video_style=video_style,
                quality=quality
            )
            
            return jsonify(result), 200
            
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_hunt_video_bp.route('/api/battle-hunt-video/hunt/generate', methods=['POST'])
@rate_limit
def generate_hunt_video():
    """Generate a video from hunt/trophy achievement"""
    try:
        data = InputValidator.get_json_safe(request)
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['hunt_event'])
        if not is_valid:
            return ErrorHandler.create_error_response(error_msg, 400)
        
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        hunt_event = data.get('hunt_event', {})
        video_style = InputValidator.sanitize_string(data.get('video_style', 'adventure'))
        quality = InputValidator.sanitize_string(data.get('quality', 'medium'))
        
        # Validate video_style
        if video_style not in ['adventure', 'documentary', 'cinematic', 'celebration']:
            video_style = 'adventure'
        
        # Validate quality
        if quality not in ['low', 'medium', 'high']:
            quality = 'medium'
        
        # Generate video (can be async)
        async_mode = data.get('async', False)
        
        if async_mode:
            # Generate in background thread
            app = current_app._get_current_object()
            def generate_async():
                with app.app_context():
                    battle_hunt_video_integration.generate_hunt_video(
                        user_id=user_id,
                        hunt_event=hunt_event,
                        video_style=video_style,
                        quality=quality
                    )
            
            thread = threading.Thread(target=generate_async)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "message": "Video generation started in background",
                "status": "processing"
            }), 202
        else:
            # Generate synchronously
            result = battle_hunt_video_integration.generate_hunt_video(
                user_id=user_id,
                hunt_event=hunt_event,
                video_style=video_style,
                quality=quality
            )
            
            return jsonify(result), 200
            
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_hunt_video_bp.route('/api/battle-hunt-video/battle/<battle_id>', methods=['GET'])
@rate_limit
def get_battle_video(battle_id: str):
    """Get video data for a battle"""
    try:
        battle_id = InputValidator.sanitize_string(battle_id)
        video_data = battle_hunt_video_integration.get_battle_video(battle_id)
        
        if video_data:
            return jsonify({
                "success": True,
                "video": video_data
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Video not found for this battle"
            }), 404
            
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_hunt_video_bp.route('/api/battle-hunt-video/hunt/<hunt_id>', methods=['GET'])
@rate_limit
def get_hunt_video(hunt_id: str):
    """Get video data for a hunt event"""
    try:
        hunt_id = InputValidator.sanitize_string(hunt_id)
        video_data = battle_hunt_video_integration.get_hunt_video(hunt_id)
        
        if video_data:
            return jsonify({
                "success": True,
                "video": video_data
            }), 200
        else:
            return jsonify({
                "success": False,
                "error": "Video not found for this hunt event"
            }), 404
            
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_hunt_video_bp.route('/api/battle-hunt-video/history/<user_id>', methods=['GET'])
@rate_limit
def get_user_video_history(user_id: str):
    """Get user's battle/hunt video history"""
    try:
        user_id = InputValidator.sanitize_string(user_id)
        limit = int(request.args.get('limit', 50))
        
        history = battle_hunt_video_integration.get_user_video_history(user_id, limit)
        
        return jsonify({
            "success": True,
            "history": history,
            "count": len(history)
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_hunt_video_bp.route('/api/battle-hunt-video/battle/all', methods=['GET'])
@rate_limit
def get_all_battle_videos():
    """Get all battle videos"""
    try:
        videos = battle_hunt_video_integration.get_all_battle_videos()
        
        return jsonify({
            "success": True,
            "videos": videos,
            "count": len(videos)
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_hunt_video_bp.route('/api/battle-hunt-video/hunt/all', methods=['GET'])
@rate_limit
def get_all_hunt_videos():
    """Get all hunt videos"""
    try:
        videos = battle_hunt_video_integration.get_all_hunt_videos()
        
        return jsonify({
            "success": True,
            "videos": videos,
            "count": len(videos)
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

