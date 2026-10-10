"""
Agent Enhanced Skills Routes
API endpoints for all agent enhanced skills including manager roles
"""
from flask import Blueprint, request, jsonify
from backend.services.agent_enhanced_skills_system import agent_enhanced_skills
from src.utils.rate_limiter import rate_limit
import sys
import traceback

agent_enhanced_skills_bp = Blueprint('agent_enhanced_skills', __name__)


@agent_enhanced_skills_bp.route('/api/agent/enhanced-skills', methods=['GET'])
@agent_enhanced_skills_bp.route('/vidgenerator/api/agent/enhanced-skills', methods=['GET'])
@rate_limit()
def get_all_enhanced_skills():
    """Get all enhanced skills for an agent"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = agent_enhanced_skills.get_all_skills(user_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[EnhancedSkills] Error: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_enhanced_skills_bp.route('/api/agent/manager-roles', methods=['GET'])
@agent_enhanced_skills_bp.route('/vidgenerator/api/agent/manager-roles', methods=['GET'])
@rate_limit()
def get_all_manager_roles():
    """Get all available manager roles"""
    try:
        from backend.services.agent_enhanced_skills_system import AgentEnhancedSkillsSystem
        roles = AgentEnhancedSkillsSystem.MANAGER_ROLES
        return jsonify({'success': True, 'roles': roles, 'total': len(roles)}), 200
    except Exception as e:
        print(f"[AgentEnhancedSkillsRoutes] Error getting manager roles: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_enhanced_skills_bp.route('/api/agent/manager-roles/agent', methods=['GET'])
@agent_enhanced_skills_bp.route('/vidgenerator/api/agent/manager-roles/agent', methods=['GET'])
@rate_limit()
def get_agent_manager_roles():
    """Get manager roles for a specific agent"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        agent_id = request.args.get('agent_id')
        if not agent_id:
            return jsonify({'success': False, 'message': 'agent_id is required'}), 400
        result = agent_enhanced_skills.get_agent_manager_roles(user_id, agent_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[AgentEnhancedSkillsRoutes] Error getting agent manager roles: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_enhanced_skills_bp.route('/api/agent/manager-roles/unlock', methods=['POST'])
@agent_enhanced_skills_bp.route('/vidgenerator/api/agent/manager-roles/unlock', methods=['POST'])
@rate_limit()
def unlock_manager_role():
    """Unlock a manager role for an agent"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        role_id = data.get('role_id')
        if not all([agent_id, role_id]):
            return jsonify({'success': False, 'message': 'agent_id and role_id are required'}), 400
        result = agent_enhanced_skills.unlock_manager_role(user_id, agent_id, role_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[AgentEnhancedSkillsRoutes] Error unlocking manager role: {e}", file=sys.stderr, flush=True)
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
