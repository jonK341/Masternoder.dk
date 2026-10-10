"""
Routes for Ultra Resource Controller
Mind points, energy management, passive income nodes
"""
from flask import Blueprint, jsonify, request
from backend.services.ultra_resource_controller import ultra_resource_controller

ultra_resource_bp = Blueprint('ultra_resource', __name__, url_prefix='/api/ultra-resource')


@ultra_resource_bp.route('/energy', methods=['GET'])
def get_energy_status():
    """Get energy status"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = ultra_resource_controller.get_energy_status(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ultra_resource_bp.route('/node/create', methods=['POST'])
def create_node():
    """Create passive income node"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        node_type = data.get('node_type')
        node_data = data.get('node_data', {})
        
        if not node_type:
            return jsonify({
                'success': False,
                'error': 'node_type required'
            }), 400
        
        result = ultra_resource_controller.create_node(user_id, node_type, node_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ultra_resource_bp.route('/income/generate', methods=['POST'])
def generate_passive_income():
    """Generate passive income from nodes"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        result = ultra_resource_controller.generate_passive_income(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ultra_resource_bp.route('/content/create', methods=['POST'])
def create_modular_content():
    """Create modular content (Lego-Robot logic)"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        content_data = data.get('content_data', {})
        
        result = ultra_resource_controller.create_modular_content(user_id, content_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ultra_resource_bp.route('/ai-simplifier', methods=['POST'])
def create_ai_simplifier():
    """Create AI simplifier prompt (The 1% AI Hack)"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        prompt_data = data.get('prompt_data', {})
        
        result = ultra_resource_controller.create_ai_simplifier_prompt(user_id, prompt_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ultra_resource_bp.route('/automation/create', methods=['POST'])
def create_automation():
    """Create automation task"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        task_data = data.get('task_data', {})
        
        result = ultra_resource_controller.create_automation_task(user_id, task_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ultra_resource_bp.route('/summary', methods=['GET'])
def get_resource_summary():
    """Get complete resource summary"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = ultra_resource_controller.get_resource_summary(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

