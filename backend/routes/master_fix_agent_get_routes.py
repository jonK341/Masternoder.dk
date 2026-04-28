"""
Master Fix Agent Get Routes
GET endpoints for agent information (personality, missions, quests, history, statistics, behavior)
"""
from flask import Blueprint, jsonify, request
from backend.services.master_fix_agent_skills import master_fix_agent_skills

master_fix_get_bp = Blueprint('master_fix_get', __name__)


@master_fix_get_bp.route('/api/agent/master-fix/personality', methods=['GET'])
def get_personality():
    """Get agent personality"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_personality'):
            try:
                result = master_fix_agent_skills.skill_get_personality()
                return jsonify({
                    'success': True,
                    'personality': result
                }), 200
            except Exception as e:
                print(f"[WARN] Error in skill_get_personality: {e}")
        else:
            return jsonify({
                'success': True,
                'personality': {
                    'agent_id': 'agent_manager',
                    'name': 'Agent Manager',
                    'traits': ['helpful', 'efficient', 'organized'],
                    'status': 'active'
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@master_fix_get_bp.route('/api/agent/master-fix/missions', methods=['GET'])
def get_missions():
    """Get agent missions"""
    try:
        status = request.args.get('status', 'all')
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_missions'):
            try:
                result = master_fix_agent_skills.skill_get_missions(status)
                return jsonify(result), 200
            except Exception as e:
                print(f"[WARN] Error in skill_get_missions: {e}")
        else:
            return jsonify({
                'success': True,
                'missions': [],
                'count': 0,
                'status': status
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@master_fix_get_bp.route('/api/agent/master-fix/quests', methods=['GET'])
def get_quests():
    """Get agent quests"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_quests'):
            try:
                result = master_fix_agent_skills.skill_get_quests()
                return jsonify({
                    'success': True,
                    'quests': result
                }), 200
            except Exception as e:
                print(f"[WARN] Error in skill_get_quests: {e}")
        else:
            return jsonify({
                'success': True,
                'quests': [],
                'count': 0
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@master_fix_get_bp.route('/api/agent/master-fix/history', methods=['GET'])
def get_history():
    """Get agent history"""
    try:
        if hasattr(master_fix_agent_skills, 'skill_get_history'):
            result = master_fix_agent_skills.skill_get_history()
            return jsonify({
                'success': True,
                'history': result
            }), 200
        else:
            return jsonify({
                'success': True,
                'history': [],
                'count': 0
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@master_fix_get_bp.route('/api/agent/master-fix/statistics', methods=['GET'])
def get_statistics():
    """Get agent statistics"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_statistics'):
            try:
                result = master_fix_agent_skills.skill_get_statistics()
                return jsonify({
                    'success': True,
                    'statistics': result
                }), 200
            except Exception as e:
                print(f"[WARN] Error in skill_get_statistics: {e}")
        else:
            # Fallback with try-except
            try:
                from backend.services.agent_manager import AgentManager
                agent_manager = AgentManager()
                if hasattr(agent_manager, 'data'):
                    agent_data = agent_manager.data
                else:
                    agent_data = {}
            except (ImportError, Exception) as e:
                print(f"[WARN] Could not import AgentManager: {e}")
                agent_data = {}
            
            return jsonify({
                'success': True,
                'statistics': {
                    'agent_id': 'agent_manager',
                    'level': agent_data.get('level', 1),
                    'experience': agent_data.get('experience', 0),
                    'tasks_completed': agent_data.get('tasks_completed', 0),
                    'status': 'active'
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@master_fix_get_bp.route('/api/agent/master-fix/behavior-pattern', methods=['GET'])
def get_behavior_pattern():
    """Get agent behavior pattern"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_behavior'):
            try:
                result = master_fix_agent_skills.skill_get_behavior()
                return jsonify({
                    'success': True,
                    'behavior': result
                }), 200
            except Exception as e:
                print(f"[WARN] Error in skill_get_behavior: {e}")
        else:
            return jsonify({
                'success': True,
                'behavior': {
                    'pattern': 'balanced',
                    'aggressiveness': 0.5,
                    'caution': 0.5,
                    'status': 'active'
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@master_fix_get_bp.route('/api/agent/master-fix/fix-history', methods=['GET'])
def get_fix_history():
    """Get fix history (alias for history)"""
    return get_history()


@master_fix_get_bp.route('/api/agent/master-fix/fix-behavior', methods=['GET'])
def get_fix_behavior():
    """Get fix behavior (alias for behavior-pattern)"""
    return get_behavior_pattern()
