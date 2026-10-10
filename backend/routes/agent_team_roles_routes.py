"""
Agent Team Roles Routes
API endpoints for Team Manager and Secretary agent types
"""
from flask import Blueprint, request, jsonify
from backend.services.agent_team_roles_system import agent_team_roles_system
from src.utils.rate_limiter import rate_limit
import sys

agent_team_roles_bp = Blueprint('agent_team_roles', __name__)

@agent_team_roles_bp.route('/api/agent-team-roles/types', methods=['GET'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/types', methods=['GET'])
@rate_limit()
def get_agent_types():
    """Get all available agent types"""
    try:
        result = agent_team_roles_system.get_all_agent_types()
        return jsonify(result), 200
    except Exception as e:
        print(f"[AgentTeamRoles] Error getting agent types: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/type/<agent_type_id>', methods=['GET'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/type/<agent_type_id>', methods=['GET'])
@rate_limit()
def get_agent_type(agent_type_id):
    """Get specific agent type definition"""
    try:
        agent_type = agent_team_roles_system.get_agent_type(agent_type_id)
        if agent_type:
            return jsonify({
                'success': True,
                'agent_type': agent_type
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Agent type not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/create', methods=['POST'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/create', methods=['POST'])
@rate_limit()
def create_team_role_agent():
    """Create a new team role agent (Team Manager or Secretary)"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_name = data.get('agent_name', 'My Agent')
        agent_type_id = data.get('agent_type', 'team_manager')
        
        if agent_type_id not in ['team_manager', 'secretary']:
            return jsonify({
                'success': False,
                'error': 'Invalid agent type. Must be "team_manager" or "secretary"'
            }), 400
        
        result = agent_team_roles_system.create_agent(user_id, agent_name, agent_type_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        print(f"[AgentTeamRoles] Error creating agent: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/<agent_id>/activity', methods=['POST'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/<agent_id>/activity', methods=['POST'])
@rate_limit()
def perform_activity(agent_id):
    """Agent performs an activity"""
    try:
        data = request.get_json() or {}
        activity_name = data.get('activity_name')
        
        if not activity_name:
            return jsonify({
                'success': False,
                'error': 'activity_name required'
            }), 400
        
        result = agent_team_roles_system.perform_activity(agent_id, activity_name)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/<agent_id>/ability', methods=['POST'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/<agent_id>/ability', methods=['POST'])
@rate_limit()
def use_ability(agent_id):
    """Agent uses an ability"""
    try:
        data = request.get_json() or {}
        ability_id = data.get('ability_id')
        
        if not ability_id:
            return jsonify({
                'success': False,
                'error': 'ability_id required'
            }), 400
        
        result = agent_team_roles_system.use_ability(agent_id, ability_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/<agent_id>/battle-action', methods=['POST'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/<agent_id>/battle-action', methods=['POST'])
@rate_limit()
def use_battle_action(agent_id):
    """Agent uses a battle action"""
    try:
        data = request.get_json() or {}
        action_id = data.get('action_id')
        battle_context = data.get('battle_context', {})
        
        if not action_id:
            return jsonify({
                'success': False,
                'error': 'action_id required'
            }), 400
        
        result = agent_team_roles_system.use_battle_action(agent_id, action_id, battle_context)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/<agent_id>', methods=['GET'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/<agent_id>', methods=['GET'])
@rate_limit()
def get_agent_info(agent_id):
    """Get full agent information"""
    try:
        result = agent_team_roles_system.get_agent_info(agent_id)
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_team_roles_bp.route('/api/agent-team-roles/user/<user_id>', methods=['GET'])
@agent_team_roles_bp.route('/vidgenerator/api/agent-team-roles/user/<user_id>', methods=['GET'])
@rate_limit()
def get_user_agents(user_id):
    """Get all team role agents for a user"""
    try:
        result = agent_team_roles_system.get_user_agents(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
