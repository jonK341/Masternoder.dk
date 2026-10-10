"""
Time Disorder Device and Advanced Battle Tech Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.time_disorder_device import time_disorder_device
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

time_disorder_battle_bp = Blueprint('time_disorder_battle', __name__)


@time_disorder_battle_bp.route('/api/battle/time-disorder/create', methods=['POST'])
@rate_limit
def create_time_disorder_device():
    """Create Time Disorder Device"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        device_name = data.get('device_name', 'Time Disorder Device Alpha')
        power_level = int(data.get('power_level', 100))
        
        result = time_disorder_device.create_time_disorder_device(user_id, device_name, power_level)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@time_disorder_battle_bp.route('/api/battle/time-disorder/activate', methods=['POST'])
@rate_limit
def activate_time_disorder():
    """Activate time disorder"""
    try:
        data = InputValidator.get_json_safe(request)
        device_id = InputValidator.sanitize_string(data.get('device_id', ''))
        disorder_type = data.get('disorder_type', 'temporal_dilation')
        intensity = float(data.get('intensity', 1.0))
        
        if not device_id:
            return jsonify({'success': False, 'error': 'device_id required'}), 400
        
        result = time_disorder_device.activate_time_disorder(device_id, disorder_type, intensity)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@time_disorder_battle_bp.route('/api/battle/shield/combine', methods=['POST'])
@rate_limit
def combine_shield():
    """Combine Time Disorder Device with Death Portal as shield"""
    try:
        data = InputValidator.get_json_safe(request)
        device_id = InputValidator.sanitize_string(data.get('device_id', ''))
        portal_id = InputValidator.sanitize_string(data.get('portal_id', ''))
        shield_name = data.get('shield_name', 'Time-Death Shield')
        
        if not device_id or not portal_id:
            return jsonify({'success': False, 'error': 'device_id and portal_id required'}), 400
        
        result = time_disorder_device.combine_with_death_portal_shield(device_id, portal_id, shield_name)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@time_disorder_battle_bp.route('/api/battle/shield/<shield_id>/status', methods=['GET'])
def get_shield_status(shield_id):
    """Get shield status"""
    try:
        result = time_disorder_device.get_shield_status(shield_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@time_disorder_battle_bp.route('/api/battle/tech-hole/create', methods=['POST'])
@rate_limit
def create_tech_hole():
    """Create tech hole for new tech incoming"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        hole_type = data.get('hole_type', 'new_tech_incoming')
        location = data.get('location')
        
        result = time_disorder_device.create_tech_hole(user_id, hole_type, location)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@time_disorder_battle_bp.route('/api/battle/tech-hole/<hole_id>/receive-tech', methods=['POST'])
@time_disorder_battle_bp.route('/vidgenerator/api/battle/tech-hole/<hole_id>/receive-tech', methods=['POST'])
@rate_limit
def receive_new_tech(hole_id):
    """Receive new technology through hole"""
    try:
        data = InputValidator.get_json_safe(request)
        tech_name = InputValidator.sanitize_string(data.get('tech_name', ''))
        tech_data = data.get('tech_data', {})
        
        if not tech_name:
            return jsonify({'success': False, 'error': 'tech_name required'}), 400
        
        result = time_disorder_device.receive_new_tech(hole_id, tech_name, tech_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@time_disorder_battle_bp.route('/api/battle/tech-hole', methods=['GET'])
@time_disorder_battle_bp.route('/vidgenerator/api/battle/tech-hole', methods=['GET'])
def get_tech_holes():
    """Get all tech holes"""
    try:
        user_id = request.args.get('user_id')
        result = time_disorder_device.get_tech_holes(user_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


# Advanced Battle Tech routes moved to advanced_battle_tech_routes.py
# Routes moved: unlock, combine, available, list, status, impressiveness
# These routes are now in backend/routes/advanced_battle_tech_routes.py
# Impressiveness endpoint also moved to advanced_battle_tech_routes.py

