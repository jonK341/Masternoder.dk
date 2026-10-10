"""
Space-Time Battlegrounds Routes - API endpoints for space-time expanded warzones
"""
from flask import Blueprint, request, jsonify
from backend.services.space_time_battlegrounds import space_time_battlegrounds
from backend.utils.input_validator import InputValidator
from backend.utils.error_handler import ErrorHandler
from backend.utils.rate_limiter import rate_limit

space_time_bp = Blueprint('space_time', __name__)


@space_time_bp.route('/api/space-time/create', methods=['POST'])
@rate_limit
def create_battleground():
    """Create a Space-Time battleground"""
    try:
        data = InputValidator.get_json_safe(request)
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id'))
        name = InputValidator.sanitize_string(data.get('name', 'Space-Time Battleground'))
        guild_id = InputValidator.sanitize_string(data.get('guild_id'))
        clan_id = InputValidator.sanitize_string(data.get('clan_id'))
        space_coords = data.get('space_coords')
        time_period = InputValidator.sanitize_string(data.get('time_period', 'present'))
        
        if not battleground_id or not guild_id or not clan_id:
            return ErrorHandler.create_error_response('battleground_id, guild_id, and clan_id required', 400)
        
        result = space_time_battlegrounds.create_space_time_battleground(
            battleground_id, name, guild_id, clan_id, space_coords, time_period
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/field/create', methods=['POST'])
@rate_limit
def create_field():
    """Create a Field in space-time"""
    try:
        data = InputValidator.get_json_safe(request)
        field_id = InputValidator.sanitize_string(data.get('field_id'))
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id'))
        field_type = InputValidator.sanitize_string(data.get('field_type', 'energy'))
        position = data.get('position')
        
        if not field_id or not battleground_id:
            return ErrorHandler.create_error_response('field_id and battleground_id required', 400)
        
        result = space_time_battlegrounds.create_field(field_id, battleground_id, field_type, position)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/void/create', methods=['POST'])
@rate_limit
def create_void():
    """Create a Void in space-time"""
    try:
        data = InputValidator.get_json_safe(request)
        void_id = InputValidator.sanitize_string(data.get('void_id'))
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id'))
        void_type = InputValidator.sanitize_string(data.get('void_type', 'dark'))
        position = data.get('position')
        
        if not void_id or not battleground_id:
            return ErrorHandler.create_error_response('void_id and battleground_id required', 400)
        
        result = space_time_battlegrounds.create_void(void_id, battleground_id, void_type, position)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/giga-bande-kriminel/setup', methods=['POST'])
@rate_limit
def setup_giga_bande_kriminel():
    """Setup Giga bande Kriminel Warzone"""
    try:
        data = InputValidator.get_json_safe(request)
        warzone_id = InputValidator.sanitize_string(data.get('warzone_id'))
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id'))
        intensity = float(data.get('intensity', 1.0))
        
        if not warzone_id or not battleground_id:
            return ErrorHandler.create_error_response('warzone_id and battleground_id required', 400)
        
        result = space_time_battlegrounds.setup_giga_bande_kriminel_warzone(warzone_id, battleground_id, intensity)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/nissefisse-afbetalings/setup', methods=['POST'])
@rate_limit
def setup_nissefisse_afbetalings():
    """Setup Giga NisseFisse Afbetalings Ide"""
    try:
        data = InputValidator.get_json_safe(request)
        payment_id = InputValidator.sanitize_string(data.get('payment_id'))
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id'))
        total_amount = float(data.get('total_amount', 0))
        installments = int(data.get('installments', 12))
        
        if not payment_id or not battleground_id:
            return ErrorHandler.create_error_response('payment_id and battleground_id required', 400)
        
        result = space_time_battlegrounds.setup_nissefisse_afbetalings(
            payment_id, battleground_id, total_amount, installments
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/nissefisse-afbetalings/process', methods=['POST'])
@rate_limit
def process_installment():
    """Process installment payment"""
    try:
        data = InputValidator.get_json_safe(request)
        payment_id = InputValidator.sanitize_string(data.get('payment_id'))
        amount = float(data.get('amount', 0))
        
        if not payment_id:
            return ErrorHandler.create_error_response('payment_id required', 400)
        
        result = space_time_battlegrounds.process_installment(payment_id, amount)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/time-dilation/create', methods=['POST'])
@rate_limit
def create_time_dilation_zone():
    """Create a time dilation zone"""
    try:
        data = InputValidator.get_json_safe(request)
        zone_id = InputValidator.sanitize_string(data.get('zone_id'))
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id'))
        dilation_factor = float(data.get('dilation_factor', 1.0))
        position = data.get('position')
        
        if not zone_id or not battleground_id:
            return ErrorHandler.create_error_response('zone_id and battleground_id required', 400)
        
        result = space_time_battlegrounds.create_time_dilation_zone(
            zone_id, battleground_id, dilation_factor, position
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@space_time_bp.route('/api/space-time/battleground/<battleground_id>', methods=['GET'])
@rate_limit
def get_battleground(battleground_id: str):
    """Get space-time battleground with all fields and voids"""
    try:
        result = space_time_battlegrounds.get_space_time_battleground(battleground_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

