"""
Agent Behavior Routes
API endpoints for agent player behavior simulation
"""
from flask import Blueprint, jsonify, request, current_app
from backend.services.agent_player_behavior import agent_player_behavior
from backend.services.agent_behavior_executor import agent_behavior_executor
from src.db.models import db
from datetime import datetime

agent_behavior_bp = Blueprint('agent_behavior', __name__)

@agent_behavior_bp.route('/api/agents/behavior/simulate-session', methods=['POST'])
def simulate_session():
    """Simulate an agent session"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id', f"agent_{datetime.now().timestamp()}")
        behavior_type = data.get('behavior_type')
        
        session_plan = agent_player_behavior.generate_session_plan(agent_id, behavior_type)
        
        # Optionally execute the session and save to database
        if data.get('execute', False):
            with current_app.app_context():
                result = agent_behavior_executor.execute_and_save_session(agent_id, db)
                if result.get('success'):
                    session_plan['execution_results'] = result
                else:
                    # Fallback to in-memory execution
                    results = agent_player_behavior.execute_session(agent_id, session_plan)
                    session_plan['execution_results'] = results
        
        return jsonify({
            'success': True,
            'session_plan': session_plan
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_behavior_bp.route('/api/agents/behavior/simulate-day', methods=['POST'])
def simulate_day():
    """Simulate a full day of agent activity"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id', f"agent_{datetime.now().timestamp()}")
        
        daily_activity = agent_player_behavior.simulate_daily_activity(agent_id)
        
        return jsonify({
            'success': True,
            'daily_activity': daily_activity
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_behavior_bp.route('/api/agents/behavior/execute-action', methods=['POST'])
def execute_action():
    """Execute a single agent action"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        action = data.get('action')
        
        if not agent_id or not action:
            return jsonify({
                'success': False,
                'error': 'agent_id and action are required'
            }), 400
        
        result = agent_player_behavior.execute_action(agent_id, action)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_behavior_bp.route('/api/agents/behavior/get-behavior-type', methods=['GET'])
def get_behavior_type():
    """Get behavior type for an agent"""
    try:
        agent_id = request.args.get('agent_id')
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        behavior_type = agent_player_behavior.get_behavior_type(agent_id)
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'behavior_type': behavior_type,
            'pattern': agent_player_behavior.behavior_patterns[behavior_type]
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_behavior_bp.route('/api/agents/behavior/should-be-active', methods=['GET'])
def should_be_active():
    """Check if agent should be active now"""
    try:
        agent_id = request.args.get('agent_id')
        behavior_type = request.args.get('behavior_type')
        
        if not agent_id and not behavior_type:
            return jsonify({
                'success': False,
                'error': 'agent_id or behavior_type is required'
            }), 400
        
        if not behavior_type:
            behavior_type = agent_player_behavior.get_behavior_type(agent_id)
        
        is_active = agent_player_behavior.should_be_active_now(behavior_type)
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'behavior_type': behavior_type,
            'should_be_active': is_active,
            'current_hour': datetime.now().hour
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_behavior_bp.route('/api/agents/behavior/batch', methods=['GET'])
def behavior_batch():
    """Batch get behavior type + should-be-active for multiple agents (reduces 40 requests to 1)."""
    try:
        agent_ids_str = request.args.get('agent_ids', '')
        if not agent_ids_str:
            return jsonify({'success': True, 'agents': []}), 200
        agent_ids = [a.strip() for a in agent_ids_str.split(',') if a.strip()][:50]
        agents = []
        for agent_id in agent_ids:
            try:
                behavior_type = agent_player_behavior.get_behavior_type(agent_id)
                should_be_active = agent_player_behavior.should_be_active_now(behavior_type)
                agents.append({
                    'agent_id': agent_id,
                    'behavior_type': behavior_type,
                    'should_be_active': should_be_active,
                })
            except Exception:
                agents.append({
                    'agent_id': agent_id,
                    'behavior_type': 'unknown',
                    'should_be_active': False,
                })
        return jsonify({
            'success': True,
            'agents': agents,
            'current_hour': datetime.now().hour,
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
