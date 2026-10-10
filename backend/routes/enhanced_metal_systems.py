"""
Enhanced Metal Systems Routes - API endpoints for all metal systems
"""
from flask import Blueprint, request, jsonify
from backend.services.enhanced_metal_systems import enhanced_metal_systems
from backend.utils.input_validator import InputValidator
from backend.utils.error_handler import ErrorHandler
from backend.utils.rate_limiter import rate_limit

enhanced_metal_bp = Blueprint('enhanced_metal', __name__)


@enhanced_metal_bp.route('/api/enhanced-metal/initialize', methods=['POST'])
@rate_limit
def initialize_user():
    """Initialize user with all metal systems"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        
        result = enhanced_metal_systems.initialize_user(user_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/gps/update', methods=['POST'])
@rate_limit
def update_gps():
    """Update International GPS location"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        country = InputValidator.sanitize_string(data.get('country'))
        city = InputValidator.sanitize_string(data.get('city'))
        
        result = enhanced_metal_systems.update_gps_location(user_id, lat, lng, country, city)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/territory/add-points', methods=['POST'])
@rate_limit
def add_territory_points():
    """Add points to Territory Metal"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        points = int(data.get('points', 0))
        
        result = enhanced_metal_systems.add_territory_metal_points(user_id, points)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/sex/add-points', methods=['POST'])
@rate_limit
def add_sex_points():
    """Add points to Sex Metal"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        points = int(data.get('points', 0))
        
        result = enhanced_metal_systems.add_sex_metal_points(user_id, points)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/porno-rights/add-points', methods=['POST'])
@rate_limit
def add_porno_rights_points():
    """Add points to Porno Rights Metal"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        points = int(data.get('points', 0))
        
        result = enhanced_metal_systems.add_porno_rights_metal_points(user_id, points)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/mtg/add-points', methods=['POST'])
@rate_limit
def add_mtg_points():
    """Add points to MTG Metal"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        points = int(data.get('points', 0))
        
        result = enhanced_metal_systems.add_mtg_metal_points(user_id, points)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/trophy-hunt/add-points', methods=['POST'])
@rate_limit
def add_trophy_hunt_points():
    """Add points to Trophy Hunt Metal"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        points = int(data.get('points', 0))
        
        result = enhanced_metal_systems.add_trophy_hunt_metal_points(user_id, points)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/street-minds/connect', methods=['POST'])
@rate_limit
def connect_street_minds():
    """Connect Street Minds with metal systems"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        metal_type = InputValidator.sanitize_string(data.get('metal_type'))
        
        if not metal_type:
            return ErrorHandler.create_error_response('metal_type required', 400)
        
        result = enhanced_metal_systems.connect_street_minds(user_id, metal_type)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/stats', methods=['GET'])
@rate_limit
def get_all_stats():
    """Get all metal system stats"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        result = enhanced_metal_systems.get_all_metal_stats(user_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/refresh-hash', methods=['GET'])
@rate_limit
def get_refresh_hash():
    """Get refresh hash for system(s)"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        system = InputValidator.sanitize_string(request.args.get('system'))
        
        result = enhanced_metal_systems.get_refresh_hash(user_id, system)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/zero-points/update', methods=['POST'])
@rate_limit
def update_zero_points_stat():
    """Update a zero points stat"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        stat_name = InputValidator.sanitize_string(data.get('stat_name'))
        value = data.get('value')
        increment = data.get('increment')
        
        if not stat_name:
            return ErrorHandler.create_error_response('stat_name required', 400)
        
        result = enhanced_metal_systems.update_zero_points_stat(user_id, stat_name, value, increment)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/zero-points/stats', methods=['GET'])
@rate_limit
def get_zero_points_stats():
    """Get all zero points stats"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        result = enhanced_metal_systems.get_zero_points_stats(user_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@enhanced_metal_bp.route('/api/enhanced-metal/zero-points/increment-multiple', methods=['POST'])
@rate_limit
def increment_multiple_stats():
    """Increment multiple zero points stats at once"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        stats_updates = data.get('stats_updates', {})
        
        if not stats_updates or not isinstance(stats_updates, dict):
            return ErrorHandler.create_error_response('stats_updates must be a dictionary', 400)
        
        result = enhanced_metal_systems.increment_multiple_stats(user_id, stats_updates)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

