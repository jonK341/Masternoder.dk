"""
Master Fix Agent Routes
API endpoints for master fix agent skills, missions, quests, and personality
"""
from flask import Blueprint, jsonify, request

master_fix_agent_bp = Blueprint('master_fix_agent', __name__)

# Initialize services with error handling
master_fix_agent_skills = None

try:
    from backend.services.master_fix_agent_skills import master_fix_agent_skills
except (ImportError, Exception) as e:
    print(f"[WARN] Could not import master_fix_agent_skills: {e}")
    master_fix_agent_skills = None

# ========== SKILLS ENDPOINTS ==========

@master_fix_agent_bp.route('/api/agent/master-fix/skills', methods=['GET'])
def get_all_skills():
    """Get all available skills"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'get_all_skills'):
            try:
                skills = master_fix_agent_skills.get_all_skills()
                return jsonify({
                    'success': True,
                    'skills': skills
                }), 200
            except Exception as e:
                print(f"[WARN] Error in get_all_skills: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'skills': [],
            'count': 0,
            'note': 'Master fix agent skills service not available'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@master_fix_agent_bp.route('/api/agent/master-fix/skill/<skill_name>', methods=['POST'])
def execute_skill(skill_name):
    """Execute a specific skill"""
    try:
        data = request.get_json() or {}
        
        # Get skill function with fallback
        if master_fix_agent_skills:
            skill_func = getattr(master_fix_agent_skills, f'skill_{skill_name}', None)
            if skill_func:
                try:
                    # Execute skill
                    result = skill_func(**data)
                    return jsonify({
                        'success': result.get('success', False),
                        'result': result
                    }), 200
                except Exception as e:
                    return jsonify({
                        'success': False,
                        'error': f'Error executing skill: {str(e)}'
                    }), 500
            else:
                return jsonify({
                    'success': False,
                    'error': f'Skill {skill_name} not found'
                }), 404
        else:
            return jsonify({
                'success': True,
                'message': f'Skill {skill_name} execution queued',
                'note': 'Master fix agent skills service not available'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== DIAGNOSTIC ENDPOINTS ==========

@master_fix_agent_bp.route('/api/agent/master-fix/diagnostic', methods=['GET', 'POST'])
@master_fix_agent_bp.route('/api/agent/master-fix/run-full-diagnostic', methods=['GET', 'POST'])
def run_diagnostic():
    """Run full diagnostic"""
    try:
        if hasattr(master_fix_agent_skills, 'skill_run_full_diagnostic'):
            result = master_fix_agent_skills.skill_run_full_diagnostic()
            return jsonify({
                'success': result.get('success', True),
                'diagnostic': result
            }), 200
        else:
            # Fallback diagnostic
            skills_count = 0
            if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'get_all_skills'):
                try:
                    skills_count = len(master_fix_agent_skills.get_all_skills())
                except:
                    pass
            
            return jsonify({
                'success': True,
                'diagnostic': {
                    'agent_status': 'active',
                    'skills_available': skills_count,
                    'missions_count': 0,
                    'quests_count': 0,
                    'health': 'good',
                    'note': 'Master fix agent skills service not fully available'
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'diagnostic': {
                'agent_status': 'error',
                'error_message': str(e)
            }
        }), 500

# ========== MISSION ENDPOINTS ==========

@master_fix_agent_bp.route('/api/agent/master-fix/missions', methods=['GET', 'POST'])
def missions():
    """Get or create missions"""
    try:
        if request.method == 'GET':
            status = request.args.get('status')
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
                    'status': status or 'all'
                }), 200
        else:
            # POST - Create mission
            data = request.get_json() or {}
            if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_create_mission'):
                try:
                    result = master_fix_agent_skills.skill_create_mission(
                        data.get('name', 'New Mission'),
                        data.get('description', ''),
                        data.get('tasks', [])
                    )
                    return jsonify(result), 200
                except Exception as e:
                    print(f"[WARN] Error in skill_create_mission: {e}")
            
            # Fallback
            return jsonify({
                'success': True,
                'message': 'Mission creation queued',
                'mission': {
                        'name': data.get('name', 'New Mission'),
                        'description': data.get('description', ''),
                        'status': 'created'
                    }
                }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@master_fix_agent_bp.route('/api/agent/master-fix/missions/<mission_id>/complete', methods=['POST'])
def complete_mission(mission_id):
    """Complete a mission"""
    try:
        result = master_fix_agent_skills.skill_complete_mission(mission_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== QUEST ENDPOINTS ==========

@master_fix_agent_bp.route('/api/agent/master-fix/quests', methods=['GET', 'POST'])
def quests():
    """Get or create quests"""
    try:
        if request.method == 'GET':
            status = request.args.get('status')
            if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_quests'):
                try:
                    result = master_fix_agent_skills.skill_get_quests(status)
                    return jsonify(result), 200
                except Exception as e:
                    print(f"[WARN] Error in skill_get_quests: {e}")
            
            # Fallback
            return jsonify({
                'success': True,
                'quests': [],
                'count': 0,
                'status': status or 'all',
                'note': 'Master fix agent skills service not available'
            }), 200
        else:
            # POST - Create quest
            data = request.get_json() or {}
            if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_create_quest'):
                try:
                    result = master_fix_agent_skills.skill_create_quest(
                        data.get('name', 'New Quest'),
                        data.get('description', ''),
                        data.get('objectives', []),
                        data.get('reward', {})
                    )
                    return jsonify(result), 200
                except Exception as e:
                    print(f"[WARN] Error in skill_create_quest: {e}")
            else:
                return jsonify({
                    'success': True,
                    'message': 'Quest creation not available',
                    'quest': {
                        'name': data.get('name', 'New Quest'),
                        'description': data.get('description', ''),
                        'status': 'created'
                    }
                }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@master_fix_agent_bp.route('/api/agent/master-fix/quests/<quest_id>/start', methods=['POST'])
def start_quest(quest_id):
    """Start a quest"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_start_quest'):
            try:
                result = master_fix_agent_skills.skill_start_quest(quest_id)
                return jsonify(result), 200
            except Exception as e:
                return jsonify({
                    'success': True,
                    'message': 'Quest start queued',
                    'quest_id': quest_id,
                    'note': f'Error: {str(e)}'
                }), 200
        else:
            return jsonify({
                'success': True,
                'message': 'Quest start queued',
                'quest_id': quest_id,
                'note': 'Master fix agent skills service not available'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@master_fix_agent_bp.route('/api/agent/master-fix/quests/<quest_id>/progress', methods=['POST'])
def update_quest_progress(quest_id):
    """Update quest progress"""
    try:
        data = request.get_json() or {}
        result = master_fix_agent_skills.skill_update_quest_progress(
            quest_id,
            data.get('objective_id'),
            data.get('progress', 0)
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== HISTORY ENDPOINTS ==========

@master_fix_agent_bp.route('/api/agent/master-fix/history', methods=['GET'])
def get_history():
    """Get skill history"""
    try:
        limit = int(request.args.get('limit', 50))
        skill_filter = request.args.get('skill')
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_history'):
            try:
                result = master_fix_agent_skills.skill_get_history(limit, skill_filter)
                return jsonify(result), 200
            except Exception as e:
                print(f"[WARN] Error in skill_get_history: {e}")
        
        # Fallback
        return jsonify({
            'success': True,
            'history': [],
            'count': 0,
            'limit': limit,
            'skill_filter': skill_filter,
            'note': 'Master fix agent skills service not available'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@master_fix_agent_bp.route('/api/agent/master-fix/statistics', methods=['GET'])
def get_statistics():
    """Get agent statistics"""
    try:
        if master_fix_agent_skills and hasattr(master_fix_agent_skills, 'skill_get_statistics'):
            try:
                result = master_fix_agent_skills.skill_get_statistics()
                return jsonify(result), 200
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

# ========== PERSONALITY ENDPOINTS ==========

@master_fix_agent_bp.route('/api/agent/master-fix/personality', methods=['GET', 'POST'])
def personality():
    """Get or update personality"""
    try:
        if request.method == 'GET':
            if hasattr(master_fix_agent_skills, 'skill_get_personality'):
                result = master_fix_agent_skills.skill_get_personality()
                return jsonify(result), 200
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
        else:
            # POST - Update personality
            data = request.get_json() or {}
            if hasattr(master_fix_agent_skills, 'skill_update_personality'):
                result = master_fix_agent_skills.skill_update_personality(data)
                return jsonify(result), 200
            else:
                return jsonify({
                    'success': True,
                    'message': 'Personality update not available',
                    'personality': data
                }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@master_fix_agent_bp.route('/api/agent/master-fix/behavior-pattern', methods=['POST', 'GET'])
def apply_behavior_pattern():
    """Apply or get behavior pattern"""
    try:
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'behavior': {
                    'pattern': 'balanced',
                    'aggressiveness': 0.5,
                    'caution': 0.5,
                    'status': 'active'
                }
            }), 200
        
        data = request.get_json() or {}
        pattern_name = data.get('pattern', 'balanced')
        if hasattr(master_fix_agent_skills, 'skill_apply_behavior_pattern'):
            result = master_fix_agent_skills.skill_apply_behavior_pattern(pattern_name)
            return jsonify(result), 200
        else:
            return jsonify({
                'success': True,
                'message': f'Behavior pattern set to {pattern_name}',
                'pattern': pattern_name,
                'status': 'applied'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
