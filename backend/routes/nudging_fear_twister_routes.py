"""
Nudging & Fear Twister Routes
API routes for behavior nudging and scary scene leveling
"""
from flask import Blueprint, request, jsonify
from backend.services.nudging_behavior_system import nudging_behavior_system
from backend.services.fear_twister_scene_leveler import fear_twister_scene_leveler
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from datetime import datetime
import sys
import uuid

nudging_fear_twister_bp = Blueprint('nudging_fear_twister', __name__)

# ==================== NUDGING ROUTES ====================

@nudging_fear_twister_bp.route('/api/nudging/set-target', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/nudging/set-target', methods=['POST'])
@rate_limit()
def set_behavior_target():
    """Set a behavior target for nudging"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        target_behavior = InputValidator.sanitize_string(data.get('target_behavior', ''))
        nudge_type = InputValidator.sanitize_string(data.get('nudge_type', '')) or None
        strength = float(data.get('strength', 0.5))
        
        if not target_behavior:
            return jsonify({
                'success': False,
                'error': 'target_behavior required'
            }), 400
        
        result = nudging_behavior_system.set_behavior_target(
            user_id, target_behavior, nudge_type, strength
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/nudging/apply', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/nudging/apply', methods=['POST'])
@rate_limit()
def apply_nudge():
    """Apply a nudge to the user"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        context = data.get('context', {})
        
        result = nudging_behavior_system.apply_nudge(user_id, context)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/nudging/track-success', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/nudging/track-success', methods=['POST'])
@rate_limit()
def track_nudge_success():
    """Track if nudge was successful"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        nudge_id = InputValidator.sanitize_string(data.get('nudge_id', ''))
        behavior_performed = bool(data.get('behavior_performed', False))
        
        if not nudge_id:
            return jsonify({
                'success': False,
                'error': 'nudge_id required'
            }), 400
        
        result = nudging_behavior_system.track_nudge_success(
            user_id, nudge_id, behavior_performed
        )
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/nudging/user/<user_id>', methods=['GET'])
@nudging_fear_twister_bp.route('/vidgenerator/api/nudging/user/<user_id>', methods=['GET'])
@rate_limit()
def get_user_nudges(user_id: str):
    """Get all nudges and targets for a user"""
    try:
        result = nudging_behavior_system.get_user_nudges(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/nudging/update-behavior', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/nudging/update-behavior', methods=['POST'])
@rate_limit()
def update_behavior_pattern():
    """Update behavior pattern tracking"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        behavior_type = InputValidator.sanitize_string(data.get('behavior_type', ''))
        performed = bool(data.get('performed', False))
        
        if not behavior_type:
            return jsonify({
                'success': False,
                'error': 'behavior_type required'
            }), 400
        
        result = nudging_behavior_system.update_behavior_pattern(
            user_id, behavior_type, performed
        )
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# ==================== FEAR TWISTER ROUTES ====================

@nudging_fear_twister_bp.route('/api/fear-twister/initialize-scene', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/initialize-scene', methods=['POST'])
@rate_limit()
def initialize_scary_scene():
    """Initialize a scary scene with fear leveling"""
    try:
        data = InputValidator.get_json_safe(default={})
        scene_id = InputValidator.sanitize_string(data.get('scene_id', ''))
        generation_id = InputValidator.sanitize_string(data.get('generation_id', ''))
        base_fear_level = float(data.get('base_fear_level', 0.5))
        
        if not scene_id or not generation_id:
            return jsonify({
                'success': False,
                'error': 'scene_id and generation_id required'
            }), 400
        
        result = fear_twister_scene_leveler.initialize_scary_scene(
            scene_id, generation_id, base_fear_level
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/update-progress', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/update-progress', methods=['POST'])
@rate_limit()
def update_scene_progress():
    """Update scene progress with fear twister efficiency"""
    try:
        data = InputValidator.get_json_safe(default={})
        scene_id = InputValidator.sanitize_string(data.get('scene_id', ''))
        stage = InputValidator.sanitize_string(data.get('stage', ''))
        base_progress = float(data.get('base_progress', 0))
        context = data.get('context', {})
        
        if not scene_id:
            return jsonify({
                'success': False,
                'error': 'scene_id required'
            }), 400
        
        result = fear_twister_scene_leveler.update_scene_progress(
            scene_id, stage, base_progress, context
        )
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/twist-fear', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/twist-fear', methods=['POST'])
@rate_limit()
def twist_fear_level():
    """Twist/adjust fear level for more efficient leveling"""
    try:
        data = InputValidator.get_json_safe(default={})
        scene_id = InputValidator.sanitize_string(data.get('scene_id', ''))
        new_fear_level = data.get('new_fear_level')
        twist_type = InputValidator.sanitize_string(data.get('twist_type', 'increase'))
        
        if new_fear_level is not None:
            new_fear_level = float(new_fear_level)
        
        if not scene_id:
            return jsonify({
                'success': False,
                'error': 'scene_id required'
            }), 400
        
        result = fear_twister_scene_leveler.twist_fear_level(
            scene_id, new_fear_level, twist_type
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/optimize-generation', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/optimize-generation', methods=['POST'])
@rate_limit()
def optimize_generation_progress():
    """Optimize progress counter for entire generation"""
    try:
        data = InputValidator.get_json_safe(default={})
        generation_id = InputValidator.sanitize_string(data.get('generation_id', ''))
        scenes = data.get('scenes', [])
        
        if not generation_id or not scenes:
            return jsonify({
                'success': False,
                'error': 'generation_id and scenes required'
            }), 400
        
        result = fear_twister_scene_leveler.optimize_generation_progress(
            generation_id, scenes
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/scene/<scene_id>/progress', methods=['GET'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/scene/<scene_id>/progress', methods=['GET'])
@rate_limit()
def get_scene_progress(scene_id: str):
    """Get current progress data for a scene"""
    try:
        result = fear_twister_scene_leveler.get_scene_progress(scene_id)
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/generation/<generation_id>/optimization', methods=['GET'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/generation/<generation_id>/optimization', methods=['GET'])
@rate_limit()
def get_generation_optimization(generation_id: str):
    """Get optimization data for a generation"""
    try:
        result = fear_twister_scene_leveler.get_generation_optimization(generation_id)
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/calculate-progress', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/calculate-progress', methods=['POST'])
@rate_limit()
def calculate_scary_scene_progress():
    """Calculate progress for scary scene with fear twister"""
    try:
        data = InputValidator.get_json_safe(default={})
        base_progress = float(data.get('base_progress', 0))
        fear_level = float(data.get('fear_level', 0.5))
        scene_complexity = float(data.get('scene_complexity', 1.0))
        
        result = fear_twister_scene_leveler.calculate_scary_scene_progress(
            base_progress, fear_level, scene_complexity
        )
        
        return jsonify({
            'success': True,
            'calculation': result
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@nudging_fear_twister_bp.route('/api/fear-twister/batch-optimize', methods=['POST'])
@nudging_fear_twister_bp.route('/vidgenerator/api/fear-twister/batch-optimize', methods=['POST'])
@rate_limit()
def batch_optimize_scenes():
    """Batch optimize multiple scary scenes"""
    try:
        data = InputValidator.get_json_safe(default={})
        generation_id = InputValidator.sanitize_string(data.get('generation_id', ''))
        scene_configs = data.get('scene_configs', [])
        
        if not generation_id or not scene_configs:
            return jsonify({
                'success': False,
                'error': 'generation_id and scene_configs required'
            }), 400
        
        result = fear_twister_scene_leveler.batch_optimize_scenes(
            generation_id, scene_configs
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

