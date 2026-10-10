"""
Energy Generation & Agent Manager Routes
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

energy_agent_bp = Blueprint('energy_agent', __name__, url_prefix='/api/energy-agent')

# Energy Generation Routes
@energy_agent_bp.route('/energy/generate', methods=['POST'])
def generate_energy():
    """Generate energy for a user"""
    try:
        from backend.services.energy_generation_system import energy_generation_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        energy_type = data.get('energy_type', 'active')
        amount = data.get('amount')
        metadata = data.get('metadata', {})
        
        result = energy_generation_system.generate_energy(user_id, energy_type, amount, metadata)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating energy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/energy/<user_id>', methods=['GET'])
def get_user_energy(user_id: str):
    """Get user energy statistics"""
    try:
        from backend.services.energy_generation_system import energy_generation_system
        
        energy_data = energy_generation_system.get_user_energy(user_id)
        return jsonify({
            'success': True,
            'energy_data': energy_data
        })
    except Exception as e:
        logger.error(f"Error getting user energy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/energy/ability/activate', methods=['POST'])
def activate_ability():
    """Activate agent ability for energy generation"""
    try:
        from backend.services.energy_generation_system import energy_generation_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        ability_id = data.get('ability_id')
        agent_ids = data.get('agent_ids', [])
        
        if not ability_id:
            return jsonify({
                'success': False,
                'error': 'Ability ID required'
            }), 400
        
        result = energy_generation_system.activate_agent_ability(user_id, ability_id, agent_ids)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error activating ability: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/energy/abilities', methods=['GET'])
def get_abilities():
    """Get all available agent abilities"""
    try:
        from backend.services.energy_generation_system import energy_generation_system
        
        abilities = energy_generation_system.get_available_abilities()
        return jsonify({
            'success': True,
            **abilities
        })
    except Exception as e:
        logger.error(f"Error getting abilities: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Agent Manager Routes
@energy_agent_bp.route('/agent/register', methods=['POST'])
def register_agent():
    """Register a new agent"""
    try:
        from backend.services.agent_manager import agent_manager
        
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        agent_type = data.get('agent_type', 'general')
        capabilities = data.get('capabilities', [])
        metadata = data.get('metadata', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'Agent ID required'
            }), 400
        
        result = agent_manager.register_agent(agent_id, agent_type, capabilities, metadata)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error registering agent: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/model/register', methods=['POST'])
def register_model():
    """Register a new model"""
    try:
        from backend.services.agent_manager import agent_manager
        
        data = request.get_json() or {}
        model_id = data.get('model_id')
        model_type = data.get('model_type', 'general')
        capabilities = data.get('capabilities', [])
        metadata = data.get('metadata', {})
        
        if not model_id:
            return jsonify({
                'success': False,
                'error': 'Model ID required'
            }), 400
        
        result = agent_manager.register_model(model_id, model_type, capabilities, metadata)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error registering model: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/agent/<agent_id>/assign/<model_id>', methods=['POST'])
def assign_agent_to_model(agent_id: str, model_id: str):
    """Assign an agent to control a model"""
    try:
        from backend.services.agent_manager import agent_manager
        
        result = agent_manager.assign_agent_to_model(agent_id, model_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error assigning agent: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/agent/<agent_id>/dashboard', methods=['GET'])
def get_agent_dashboard(agent_id: str = None):
    """Get agent dashboard"""
    try:
        from backend.services.agent_manager import agent_manager
        
        result = agent_manager.get_agent_dashboard(agent_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/agent/dashboard', methods=['GET'])
def get_all_agents_dashboard():
    """Get all agents dashboard"""
    try:
        from backend.services.agent_manager import agent_manager
        
        result = agent_manager.get_agent_dashboard()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/agent/<agent_id>/task', methods=['POST'])
def add_task(agent_id: str):
    """Add task to agent queue"""
    try:
        from backend.services.agent_manager import agent_manager
        
        data = request.get_json() or {}
        task_type = data.get('task_type', 'general')
        task_data = data.get('task_data', {})
        
        result = agent_manager.add_task(agent_id, task_type, task_data)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@energy_agent_bp.route('/model/<model_id>/status', methods=['GET'])
def get_model_status(model_id: str):
    """Get model status"""
    try:
        from backend.services.agent_manager import agent_manager
        
        result = agent_manager.get_model_status(model_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
