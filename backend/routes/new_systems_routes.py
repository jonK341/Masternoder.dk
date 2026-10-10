"""
Routes for New Systems
- Skill Reward System
- Calendar Planner System
- Groups System
- Cognitive Behavior Scanner
- Decision Trees System
- Todos and Pause System
"""
from flask import Blueprint, jsonify, request
import uuid
from backend.services.skill_reward_system import skill_reward_system
from backend.services.calendar_planner_system import calendar_planner_system
from backend.services.groups_system import groups_system
from backend.services.cognitive_behavior_scanner import cognitive_behavior_scanner
from backend.services.decision_trees_system import decision_trees_system
from backend.services.todos_pause_system import todos_pause_system

new_systems_bp = Blueprint('new_systems', __name__)


# Skill Reward Routes
@new_systems_bp.route('/api/skill-reward/complete', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/skill-reward/complete', methods=['POST'])
def record_completion():
    """Record completion and award skill"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        task_type = data.get('task_type', 'general')
        task_id = data.get('task_id', str(uuid.uuid4()))
        completion_data = data.get('completion_data', {})
        
        result = skill_reward_system.record_completion(user_id, task_type, task_id, completion_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/skill-reward/completions', methods=['GET'])
@new_systems_bp.route('/vidgenerator/api/skill-reward/completions', methods=['GET'])
def get_completions():
    """Get user completions"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = skill_reward_system.get_user_completions(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Calendar Planner Routes
@new_systems_bp.route('/api/calendar/plan/create', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/calendar/plan/create', methods=['POST'])
def create_plan():
    """Create calendar plan"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        plan_name = data.get('plan_name')
        plan_data = data.get('plan_data', {})
        
        if not plan_name:
            return jsonify({
                'success': False,
                'error': 'plan_name required'
            }), 400
        
        result = calendar_planner_system.create_plan(user_id, plan_name, plan_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/calendar/task/schedule', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/calendar/task/schedule', methods=['POST'])
def schedule_task():
    """Schedule calendar task"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        task_data = data.get('task_data', {})
        agent_id = data.get('agent_id')
        
        result = calendar_planner_system.schedule_task(user_id, task_data, agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/calendar/task/complete', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/calendar/task/complete', methods=['POST'])
def complete_scheduled_task():
    """Complete scheduled task"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        task_id = data.get('task_id')
        agent_id = data.get('agent_id')
        
        if not task_id:
            return jsonify({
                'success': False,
                'error': 'task_id required'
            }), 400
        
        result = calendar_planner_system.complete_scheduled_task(user_id, task_id, agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/calendar/events', methods=['GET'])
@new_systems_bp.route('/vidgenerator/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """Get calendar events"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        from datetime import datetime
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        result = calendar_planner_system.get_calendar_events(user_id, start, end)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Groups Routes
@new_systems_bp.route('/api/groups/create', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/groups/create', methods=['POST'])
def create_group():
    """Create group"""
    try:
        data = request.get_json() or {}
        creator_id = data.get('user_id', 'default_user')
        group_name = data.get('group_name')
        group_data = data.get('group_data', {})
        
        if not group_name:
            return jsonify({
                'success': False,
                'error': 'group_name required'
            }), 400
        
        result = groups_system.create_group(creator_id, group_name, group_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/groups/join', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/groups/join', methods=['POST'])
def join_group():
    """Join group"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        group_id = data.get('group_id')
        
        if not group_id:
            return jsonify({
                'success': False,
                'error': 'group_id required'
            }), 400
        
        result = groups_system.join_group(user_id, group_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/groups/user', methods=['GET'])
@new_systems_bp.route('/vidgenerator/api/groups/user', methods=['GET'])
def get_user_groups():
    """Get user groups"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = groups_system.get_user_groups(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Cognitive Behavior Scanner Routes
@new_systems_bp.route('/api/scanner/scan', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/scanner/scan', methods=['POST'])
def scan_user_behavior():
    """Scan user behavior"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        scan_type = data.get('scan_type', 'full')
        
        result = cognitive_behavior_scanner.scan_user_behavior(user_id, scan_type)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/scanner/optimize', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/scanner/optimize', methods=['POST'])
def apply_optimization():
    """Apply optimization"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        optimization_id = data.get('optimization_id')
        
        if not optimization_id:
            return jsonify({
                'success': False,
                'error': 'optimization_id required'
            }), 400
        
        result = cognitive_behavior_scanner.apply_optimization(user_id, optimization_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/scanner/efficiency', methods=['GET'])
@new_systems_bp.route('/vidgenerator/api/scanner/efficiency', methods=['GET'])
def get_efficiency_report():
    """Get efficiency report"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = cognitive_behavior_scanner.get_user_efficiency_report(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Decision Trees Routes
@new_systems_bp.route('/api/decision-trees/tech', methods=['GET'])
@new_systems_bp.route('/vidgenerator/api/decision-trees/tech', methods=['GET'])
def build_tech_decision_tree():
    """Build tech decision tree"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = decision_trees_system.build_tech_decision_tree(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/decision-trees/recommendation', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/decision-trees/recommendation', methods=['POST'])
def get_decision_recommendation():
    """Get decision recommendation"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        context = data.get('context', {})
        
        result = decision_trees_system.get_decision_recommendation(user_id, context)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Todos and Pause Routes
@new_systems_bp.route('/api/todos/create', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/todos/create', methods=['POST'])
def create_todo():
    """Create todo"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        todo_data = data.get('todo_data', {})
        
        result = todos_pause_system.create_todo(user_id, todo_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/todos/pause', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/todos/pause', methods=['POST'])
def pause_todo():
    """Pause todo"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        todo_id = data.get('todo_id')
        reason = data.get('reason')
        
        if not todo_id:
            return jsonify({
                'success': False,
                'error': 'todo_id required'
            }), 400
        
        result = todos_pause_system.pause_todo(user_id, todo_id, reason)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/todos/resume', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/todos/resume', methods=['POST'])
def resume_todo():
    """Resume todo"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        todo_id = data.get('todo_id')
        
        if not todo_id:
            return jsonify({
                'success': False,
                'error': 'todo_id required'
            }), 400
        
        result = todos_pause_system.resume_todo(user_id, todo_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/todos/complete', methods=['POST'])
@new_systems_bp.route('/vidgenerator/api/todos/complete', methods=['POST'])
def complete_todo():
    """Complete todo"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        todo_id = data.get('todo_id')
        
        if not todo_id:
            return jsonify({
                'success': False,
                'error': 'todo_id required'
            }), 400
        
        result = todos_pause_system.complete_todo(user_id, todo_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@new_systems_bp.route('/api/todos/list', methods=['GET'])
@new_systems_bp.route('/vidgenerator/api/todos/list', methods=['GET'])
def get_todos():
    """Get user todos"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        status = request.args.get('status')
        
        result = todos_pause_system.get_user_todos(user_id, status)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

