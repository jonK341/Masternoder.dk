"""
Agent Controller Routes
API endpoints for agent controller
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_controller import agent_controller

# Agent real-player behavior support
try:
    from backend.services.agent_player_behavior import agent_player_behavior
except Exception:
    agent_player_behavior = None

try:
    from backend.services.agent_behavior_executor import agent_behavior_executor
except Exception:
    agent_behavior_executor = None

try:
    from src.db.models import db
except Exception:
    db = None

agent_controller_bp = Blueprint('agent_controller', __name__)

@agent_controller_bp.route('/api/agent-controller/status', methods=['GET'])
@agent_controller_bp.route('/api/agents/controller/status', methods=['GET'])  # Alternative route
def controller_status():
    """Get agent controller status"""
    try:
        result = agent_controller.get_status()
        return jsonify({'success': True, 'controller': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_controller_bp.route('/api/agent-controller/all-agents', methods=['GET'])
@agent_controller_bp.route('/api/agents/controller/all-agents', methods=['GET'])  # Alternative route
def all_agents_status():
    """Get status of all agents"""
    try:
        result = agent_controller.get_all_agents_status()
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_controller_bp.route('/api/agent-controller/execute', methods=['POST'])
def execute_skill():
    """Execute a skill on an agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        skill_name = data.get('skill_name')
        kwargs = data.get('parameters', {})
        
        if not agent_id or not skill_name:
            return jsonify({
                'success': False,
                'error': 'agent_id and skill_name are required'
            }), 400
        
        result = agent_controller.execute_agent_skill(agent_id, skill_name, **kwargs)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_controller_bp.route('/api/agent-controller/agent/<agent_id>/capabilities', methods=['GET'])
def agent_capabilities(agent_id):
    """Get capabilities of a specific agent"""
    try:
        result = agent_controller.get_agent_capabilities(agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_controller_bp.route('/api/agent-controller/calculate', methods=['POST'])
def calculate_with_agents():
    """Execute calculator updates using agents"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'agent_user')
        
        result = agent_controller.calculate_with_agents(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Agent Behavior Endpoints (served via agent_controller blueprint for stability)
# ============================================================================

@agent_controller_bp.route('/api/agents/behavior/get-behavior-type', methods=['GET'])
def agent_behavior_get_type():
    """Get behavior type for an agent"""
    try:
        agent_id = request.args.get('agent_id')
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'}), 400
        if not agent_player_behavior:
            return jsonify({'success': False, 'error': 'behavior system not available'}), 500

        behavior_type = agent_player_behavior.get_behavior_type(agent_id)
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'behavior_type': behavior_type,
            'pattern': agent_player_behavior.behavior_patterns.get(behavior_type, {})
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_controller_bp.route('/api/agents/behavior/should-be-active', methods=['GET'])
def agent_behavior_should_be_active():
    """Check if agent should be active now"""
    try:
        agent_id = request.args.get('agent_id')
        behavior_type = request.args.get('behavior_type')

        if not agent_id and not behavior_type:
            return jsonify({'success': False, 'error': 'agent_id or behavior_type is required'}), 400
        if not agent_player_behavior:
            return jsonify({'success': False, 'error': 'behavior system not available'}), 500

        if not behavior_type and agent_id:
            behavior_type = agent_player_behavior.get_behavior_type(agent_id)

        is_active = agent_player_behavior.should_be_active_now(behavior_type)
        from datetime import datetime as _dt
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'behavior_type': behavior_type,
            'should_be_active': is_active,
            'current_hour': _dt.now().hour
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_controller_bp.route('/api/agents/behavior/simulate-session', methods=['POST'])
def agent_behavior_simulate_session():
    """Simulate an agent session (optionally execute+persist)"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'}), 400

        behavior_type = data.get('behavior_type')
        execute = bool(data.get('execute', False))

        if not agent_player_behavior:
            return jsonify({'success': False, 'error': 'behavior system not available'}), 500

        session_plan = agent_player_behavior.generate_session_plan(agent_id, behavior_type)

        if execute:
            # Prefer execute+save if DB is available; fallback to in-memory execution
            if agent_behavior_executor and db:
                result = agent_behavior_executor.execute_and_save_session(agent_id, db)
                session_plan['execution_results'] = result
            else:
                results = agent_player_behavior.execute_session(agent_id, session_plan)
                session_plan['execution_results'] = results

        return jsonify({'success': True, 'session_plan': session_plan}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_controller_bp.route('/api/agents/behavior/simulate-day', methods=['POST'])
def agent_behavior_simulate_day():
    """Simulate a full day of agent activity (plan only)"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'}), 400
        if not agent_player_behavior:
            return jsonify({'success': False, 'error': 'behavior system not available'}), 500

        daily_activity = agent_player_behavior.simulate_daily_activity(agent_id)
        return jsonify({'success': True, 'daily_activity': daily_activity}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
