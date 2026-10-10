"""
Mission Controller and Operator Routes - power.force.quest
"""
from flask import Blueprint, request, jsonify
from backend.services.mission_controller_operator import mission_controller_operator
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

mission_controller_bp = Blueprint('mission_controller', __name__)


@mission_controller_bp.route('/api/mission/controller/create', methods=['POST'])
@rate_limit
def create_controller():
    """Create mission controller"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        controller_name = data.get('controller_name', 'Mission Controller One')
        
        result = mission_controller_operator.create_controller(user_id, controller_name)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/operator/create', methods=['POST'])
@rate_limit
def create_operator():
    """Create mission operator with coordinates"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        operator_name = data.get('operator_name', 'Mission Operator One')
        coordinates = data.get('coordinates')
        
        result = mission_controller_operator.create_operator(user_id, operator_name, coordinates)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/operator/<operator_id>/coordinates', methods=['POST'])
@rate_limit
def update_operator_coordinates(operator_id):
    """Update operator coordinates"""
    try:
        data = InputValidator.get_json_safe(request)
        coordinates = data.get('coordinates')
        
        if not coordinates:
            return jsonify({'success': False, 'error': 'coordinates required'}), 400
        
        result = mission_controller_operator.update_operator_coordinates(operator_id, coordinates)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/power-force-quest/create', methods=['POST'])
@rate_limit
def create_power_force_quest():
    """Create power.force.quest"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        quest_name = InputValidator.sanitize_string(data.get('quest_name', 'Power Force Quest'))
        controller_id = data.get('controller_id')
        operator_id = data.get('operator_id')
        
        result = mission_controller_operator.create_power_force_quest(
            user_id=user_id,
            quest_name=quest_name,
            controller_id=controller_id,
            operator_id=operator_id
        )
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/power-force/use', methods=['POST'])
@rate_limit
def use_power_force():
    """Use power and force in quest"""
    try:
        data = InputValidator.get_json_safe(request)
        quest_id = InputValidator.sanitize_string(data.get('quest_id', ''))
        power_amount = int(data.get('power_amount', 10))
        force_amount = int(data.get('force_amount', 10))
        action = data.get('action', 'fix')
        
        if not quest_id:
            return jsonify({'success': False, 'error': 'quest_id required'}), 400
        
        result = mission_controller_operator.use_power_force(
            quest_id=quest_id,
            power_amount=power_amount,
            force_amount=force_amount,
            action=action
        )
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/quest/create', methods=['POST'])
@rate_limit
def create_quest():
    """Create additional quest (can use template)"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        quest_name = InputValidator.sanitize_string(data.get('quest_name', 'New Quest'))
        quest_type = data.get('quest_type', 'standard')
        objectives = data.get('objectives')
        template_name = data.get('template_name')
        
        result = mission_controller_operator.create_quest(user_id, quest_name, quest_type, objectives, template_name)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/quest/templates', methods=['GET'])
def get_quest_templates():
    """Get all quest templates"""
    try:
        result = mission_controller_operator.get_quest_templates()
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/task/create', methods=['POST'])
@rate_limit
def create_task():
    """Create additional task (can use template)"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        task_name = InputValidator.sanitize_string(data.get('task_name', 'New Task'))
        task_type = data.get('task_type', 'standard')
        priority = data.get('priority', 'medium')
        quest_id = data.get('quest_id')
        template_name = data.get('template_name')
        
        result = mission_controller_operator.create_task(user_id, task_name, task_type, priority, quest_id, template_name)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/task/templates', methods=['GET'])
def get_task_templates():
    """Get all task templates"""
    try:
        result = mission_controller_operator.get_task_templates()
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/task/<task_id>/complete', methods=['POST'])
@rate_limit
def complete_task(task_id):
    """Complete a task"""
    try:
        result = mission_controller_operator.complete_task(task_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/secretary/create', methods=['POST'])
@rate_limit
def create_secretary():
    """Create secretary to track intruders and trashpassers"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        secretary_name = data.get('secretary_name', 'ZA Secretary')
        
        result = mission_controller_operator.create_secretary(user_id, secretary_name)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/secretary/<secretary_id>/track-intruder', methods=['POST'])
@rate_limit
def track_download_intruder(secretary_id):
    """Track download intruder"""
    try:
        data = InputValidator.get_json_safe(request)
        intruder_data = data.get('intruder_data', {})
        
        result = mission_controller_operator.track_download_intruder(secretary_id, intruder_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/secretary/<secretary_id>/track-trashpasser', methods=['POST'])
@rate_limit
def track_trashpasser(secretary_id):
    """Track trashpasser"""
    try:
        data = InputValidator.get_json_safe(request)
        trashpasser_data = data.get('trashpasser_data', {})
        
        result = mission_controller_operator.track_trashpasser(secretary_id, trashpasser_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/secretary/<secretary_id>/intruders', methods=['GET'])
def get_tracked_intruders(secretary_id):
    """Get tracked download intruders"""
    try:
        result = mission_controller_operator.get_tracked_intruders(secretary_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/secretary/<secretary_id>/trashpassers', methods=['GET'])
def get_tracked_trashpassers(secretary_id):
    """Get tracked trashpassers"""
    try:
        result = mission_controller_operator.get_tracked_trashpassers(secretary_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/vold-flise-metal/activate', methods=['POST'])
@rate_limit
def activate_vold_flise_metal():
    """Activate Vold Flise Metal integration"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        operator_id = data.get('operator_id')
        
        result = mission_controller_operator.activate_vold_flise_metal(user_id, operator_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/tech/unlock', methods=['POST'])
@rate_limit
def unlock_tech():
    """Unlock new technology"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        tech_name = InputValidator.sanitize_string(data.get('tech_name', ''))
        
        if not tech_name:
            return jsonify({'success': False, 'error': 'tech_name required'}), 400
        
        result = mission_controller_operator.unlock_tech(user_id, tech_name)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/tech/available', methods=['GET'])
def get_available_tech():
    """Get all available technology"""
    try:
        result = mission_controller_operator.get_available_tech()
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@mission_controller_bp.route('/api/mission/user/<user_id>', methods=['GET'])
def get_user_mission_system(user_id):
    """Get user's mission system"""
    try:
        result = mission_controller_operator.get_user_mission_system(user_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

