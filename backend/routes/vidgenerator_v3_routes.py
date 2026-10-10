"""
Video Generator v3 Ultimate Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.vidgenerator_v3_ultimate import vidgenerator_v3_ultimate
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

vidgenerator_v3_bp = Blueprint('vidgenerator_v3', __name__)

def get_user_id():
    """Get user ID from session or request"""
    from flask import session
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session.get('user_id', request.args.get('user_id', 'anonymous'))


@vidgenerator_v3_bp.route('/api/vidgenerator-v3/generate', methods=['POST'])
@vidgenerator_v3_bp.route('/vidgenerator/api/vidgenerator-v3/generate', methods=['POST'])
@rate_limit()
def generate_with_intelligence():
    """Generate content with intelligence"""
    try:
        user_id = get_user_id()
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        generation_type = data.get('generation_type', 'video')
        quality_preset = data.get('quality_preset', 'standard')
        intelligence_level = data.get('intelligence_level', 'standard')
        
        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt required'}), 400
        
        result = vidgenerator_v3_ultimate.generate_with_intelligence(
            user_id, prompt, generation_type, quality_preset, intelligence_level
        )
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@vidgenerator_v3_bp.route('/api/vidgenerator-v3/quality-presets')
@vidgenerator_v3_bp.route('/vidgenerator/api/vidgenerator-v3/quality-presets')
@rate_limit()
def get_quality_presets():
    """Get all quality presets"""
    return jsonify({
        'success': True,
        'quality_presets': vidgenerator_v3_ultimate.quality_presets
    }), 200


@vidgenerator_v3_bp.route('/api/vidgenerator-v3/generation-types')
@vidgenerator_v3_bp.route('/vidgenerator/api/vidgenerator-v3/generation-types')
@rate_limit()
def get_generation_types():
    """Get all generation types"""
    return jsonify({
        'success': True,
        'generation_types': vidgenerator_v3_ultimate.generation_types
    }), 200

