"""
Unified Generator and Quick Battle Routes
Provides integrated endpoints for both systems
"""
from flask import Blueprint, request, jsonify
from backend.services.unified_generator_battle_integration import unified_integration
try:
    from src.utils.error_handler import ErrorHandler
    from src.utils.input_validator import InputValidator
    from src.utils.rate_limiter import rate_limit
except ImportError:
    try:
        from backend.utils.error_handler import ErrorHandler
        from backend.utils.input_validator import InputValidator
        from backend.utils.rate_limiter import rate_limit
    except ImportError:
        # Fallback - create minimal versions
        class ErrorHandler:
            @staticmethod
            def create_error_response(error, status):
                return {'success': False, 'error': str(error)}, status
        class InputValidator:
            @staticmethod
            def get_json_safe(request, default=None):
                try:
                    return request.get_json() or default or {}
                except:
                    return default or {}
            @staticmethod
            def sanitize_string(value, max_length=1000):
                if not value:
                    return ''
                return str(value)[:max_length].strip()
        def rate_limit(*args, **kwargs):
            def decorator(f):
                return f
            return decorator
import sys

unified_generator_battle_bp = Blueprint('unified_generator_battle', __name__, url_prefix='')


@unified_generator_battle_bp.route('/api/unified/generate-video', methods=['POST'])
@unified_generator_battle_bp.route('/vidgenerator/api/unified/generate-video', methods=['POST'])
@rate_limit()
def generate_video_unified():
    """Generate video with Epic Gaming tracking"""
    try:
        data = InputValidator.get_json_safe(request)
        prompt = InputValidator.sanitize_string(data.get('prompt', ''), max_length=1000).strip()
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        duration = int(data.get('duration', 5))
        resolution = InputValidator.sanitize_string(data.get('resolution', '1280x768'), max_length=20).strip()
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'Prompt is required'
            }), 200
        
        result = unified_integration.generate_video_with_tracking(
            prompt=prompt,
            user_id=user_id,
            duration=duration,
            resolution=resolution
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[UnifiedRoutes] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@unified_generator_battle_bp.route('/api/unified/create-battle', methods=['POST'])
@unified_generator_battle_bp.route('/vidgenerator/api/unified/create-battle', methods=['POST'])
@rate_limit()
def create_battle_unified():
    """Create quick battle with Epic Gaming tracking"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        difficulty = InputValidator.sanitize_string(data.get('difficulty', 'balanced'), max_length=20).strip()
        opponent_type = InputValidator.sanitize_string(data.get('opponent_type', 'ai'), max_length=20).strip()
        
        result = unified_integration.create_quick_battle_with_tracking(
            user_id=user_id,
            difficulty=difficulty,
            opponent_type=opponent_type
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[UnifiedRoutes] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@unified_generator_battle_bp.route('/api/unified/complete-battle', methods=['POST'])
@unified_generator_battle_bp.route('/vidgenerator/api/unified/complete-battle', methods=['POST'])
@rate_limit()
def complete_battle_unified():
    """Complete battle with Epic Gaming tracking"""
    try:
        data = InputValidator.get_json_safe(request)
        battle_id = data.get('battle_id')
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        won = bool(data.get('won', False))
        duration = float(data.get('duration', 0.0))
        moves = int(data.get('moves', 0))
        
        if not battle_id:
            return jsonify({
                'success': False,
                'error': 'battle_id is required'
            }), 200
        
        result = unified_integration.complete_battle_with_tracking(
            battle_id=battle_id,
            user_id=user_id,
            won=won,
            duration=duration,
            moves=moves
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[UnifiedRoutes] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@unified_generator_battle_bp.route('/api/unified/stats', methods=['GET'])
@unified_generator_battle_bp.route('/vidgenerator/api/unified/stats', methods=['GET'])
@rate_limit()
def get_unified_stats():
    """Get unified stats for generator and battle"""
    try:
        user_id = InputValidator.sanitize_string(
            request.args.get('user_id', 'default_user'),
            max_length=50
        ).strip()
        
        stats = unified_integration.get_unified_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
        
    except Exception as e:
        print(f"[UnifiedRoutes] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@unified_generator_battle_bp.route('/api/unified/status', methods=['GET'])
@unified_generator_battle_bp.route('/vidgenerator/api/unified/status', methods=['GET'])
def get_services_status():
    """Get status of all integrated services"""
    try:
        status = unified_integration.check_services_status()
        
        return jsonify({
            'success': True,
            'services': status,
            'all_available': all(status.values())
        }), 200
        
    except Exception as e:
        print(f"[UnifiedRoutes] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200
