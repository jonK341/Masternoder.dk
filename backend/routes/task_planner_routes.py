"""
Task Planner Routes
API for comprehensive task planning and scheduling
"""
from flask import Blueprint, jsonify, request
from backend.services.comprehensive_task_planner import (
    comprehensive_task_planner, TaskPriority, TaskStatus
)
from datetime import datetime, timedelta

task_planner_bp = Blueprint('task_planner', __name__)


@task_planner_bp.route('/api/tasks/create', methods=['POST'])
@task_planner_bp.route('/vidgenerator/api/tasks/create', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        data = request.get_json() or {}
        title = data.get('title')
        description = data.get('description', '')
        priority = TaskPriority(data.get('priority', 'medium'))
        estimated_duration = data.get('estimated_duration')  # in seconds
        dependencies = data.get('dependencies', [])
        assignee = data.get('assignee')
        
        if not title:
            return jsonify({'success': False, 'error': 'title required'}), 400
        
        duration = timedelta(seconds=estimated_duration) if estimated_duration else None
        
        task_id = comprehensive_task_planner.create_task(
            title, description, priority, duration, dependencies, assignee
        )
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'task': comprehensive_task_planner.tasks[task_id]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@task_planner_bp.route('/api/tasks/schedule', methods=['POST'])
@task_planner_bp.route('/vidgenerator/api/tasks/schedule', methods=['POST'])
def schedule_task():
    """Schedule a task"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        
        if not task_id or not start_time_str:
            return jsonify({'success': False, 'error': 'task_id and start_time required'}), 400
        
        start_time = datetime.fromisoformat(start_time_str)
        end_time = datetime.fromisoformat(end_time_str) if end_time_str else None
        
        result = comprehensive_task_planner.schedule_task(task_id, start_time, end_time)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@task_planner_bp.route('/api/tasks/start', methods=['POST'])
@task_planner_bp.route('/vidgenerator/api/tasks/start', methods=['POST'])
def start_task():
    """Start a task"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'task_id required'}), 400
        
        result = comprehensive_task_planner.start_task(task_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@task_planner_bp.route('/api/tasks/complete', methods=['POST'])
@task_planner_bp.route('/vidgenerator/api/tasks/complete', methods=['POST'])
def complete_task():
    """Complete a task"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        
        if not task_id:
            return jsonify({'success': False, 'error': 'task_id required'}), 400
        
        result = comprehensive_task_planner.complete_task(task_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@task_planner_bp.route('/api/tasks/plan/<task_id>', methods=['GET'])
@task_planner_bp.route('/vidgenerator/api/tasks/plan/<task_id>', methods=['GET'])
def get_task_plan(task_id: str):
    """Get task plan with dependencies"""
    try:
        result = comprehensive_task_planner.get_task_plan(task_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@task_planner_bp.route('/api/tasks/schedule', methods=['GET'])
@task_planner_bp.route('/vidgenerator/api/tasks/schedule', methods=['GET'])
def get_schedule():
    """Get schedule for date range"""
    try:
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        if not start_date_str:
            start_date = datetime.utcnow()
        else:
            start_date = datetime.fromisoformat(start_date_str)
        
        if not end_date_str:
            end_date = start_date + timedelta(days=7)
        else:
            end_date = datetime.fromisoformat(end_date_str)
        
        result = comprehensive_task_planner.get_schedule(start_date, end_date)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

