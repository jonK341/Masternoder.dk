"""
Point System Repair Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.point_system_repair import point_system_repair

point_repair_bp = Blueprint('point_repair', __name__, url_prefix='/api/point-repair')


@point_repair_bp.route('/trigger', methods=['POST'])
def trigger_points():
    """Trigger points"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        trigger_name = data.get('trigger_name', '')
        context = data.get('context', {})
        
        result = point_system_repair.trigger_points(user_id, trigger_name, context)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@point_repair_bp.route('/register-trigger', methods=['POST'])
def register_trigger():
    """Register point trigger"""
    try:
        data = request.get_json() or {}
        trigger_name = data.get('trigger_name', '')
        point_type = data.get('point_type', 'points')
        amount = data.get('amount', 0)
        
        result = point_system_repair.register_point_trigger(trigger_name, point_type, amount)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@point_repair_bp.route('/repair-counters/<user_id>', methods=['POST'])
def repair_counters(user_id: str):
    """Repair lost counters"""
    try:
        result = point_system_repair.repair_lost_counters(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@point_repair_bp.route('/final-equation/<user_id>', methods=['GET'])
def get_final_equation(user_id: str):
    """Get final equation results"""
    try:
        result = point_system_repair.get_final_equation_results(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@point_repair_bp.route('/counters/<user_id>', methods=['GET'])
def get_counters(user_id: str):
    """Get all counters"""
    try:
        result = point_system_repair.get_all_counters(user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
