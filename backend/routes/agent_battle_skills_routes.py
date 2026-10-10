"""
Agent Battle Skills Routes
API endpoints for agent battle skills
"""
from flask import Blueprint, request, jsonify
from backend.services.agent_battle_skills import agent_battle_skills
from src.utils.rate_limiter import rate_limit
import sys

agent_battle_skills_bp = Blueprint('agent_battle_skills', __name__)


@agent_battle_skills_bp.route('/api/agent/battle-skills', methods=['GET'])
@agent_battle_skills_bp.route('/vidgenerator/api/agent/battle-skills', methods=['GET'])
@rate_limit()
def get_all_battle_skills():
    """Get all available battle skills"""
    try:
        result = agent_battle_skills.get_all_battle_skills()
        return jsonify(result), 200
    except Exception as e:
        print(f"[BattleSkills] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_battle_skills_bp.route('/api/agent/battle-skills/unlock', methods=['POST'])
@agent_battle_skills_bp.route('/vidgenerator/api/agent/battle-skills/unlock', methods=['POST'])
@rate_limit()
def unlock_battle_skill():
    """Unlock a battle skill for an agent"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', request.args.get('user_id', 'default_user'))
        skill_id = data.get('skill_id')
        
        if not skill_id:
            return jsonify({
                'success': False,
                'error': 'skill_id required'
            }), 400
        
        result = agent_battle_skills.unlock_skill(user_id, skill_id)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f"[BattleSkills] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_battle_skills_bp.route('/api/agent/battle-skills/user', methods=['GET'])
@agent_battle_skills_bp.route('/vidgenerator/api/agent/battle-skills/user', methods=['GET'])
@rate_limit()
def get_user_battle_skills():
    """Get all unlocked battle skills for a user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = agent_battle_skills.get_user_skills(user_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[BattleSkills] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_battle_skills_bp.route('/api/agent/battle-skills/level-up', methods=['POST'])
@agent_battle_skills_bp.route('/vidgenerator/api/agent/battle-skills/level-up', methods=['POST'])
@rate_limit()
def level_up_battle_skill():
    """Level up a battle skill"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', request.args.get('user_id', 'default_user'))
        skill_id = data.get('skill_id')
        xp_gained = data.get('xp_gained', 10)
        
        if not skill_id:
            return jsonify({
                'success': False,
                'error': 'skill_id required'
            }), 400
        
        result = agent_battle_skills.level_up_skill(user_id, skill_id, xp_gained)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f"[BattleSkills] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
