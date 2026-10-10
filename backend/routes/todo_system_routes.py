"""
TODO System Routes
API for managing TODO items
"""
from flask import Blueprint, jsonify, request
from backend.services.todo_system_manager import (
    todo_system_manager, TodoPriority, TodoStatus
)

todo_system_bp = Blueprint('todo_system', __name__)


@todo_system_bp.route('/api/todos/create', methods=['POST'])
@todo_system_bp.route('/vidgenerator/api/todos/create', methods=['POST'])
def create_todo():
    """Create a new TODO"""
    try:
        data = request.get_json() or {}
        title = data.get('title')
        description = data.get('description', '')
        priority = TodoPriority(data.get('priority', 'medium'))
        category = data.get('category', 'features')
        dependencies = data.get('dependencies', [])
        estimated_hours = data.get('estimated_hours')
        
        if not title:
            return jsonify({'success': False, 'error': 'title required'}), 400
        
        todo_id = todo_system_manager.create_todo(
            title, description, priority, category, dependencies, estimated_hours
        )
        
        return jsonify({
            'success': True,
            'todo_id': todo_id,
            'todo': todo_system_manager.todos[todo_id]
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@todo_system_bp.route('/api/todos/update', methods=['POST'])
@todo_system_bp.route('/vidgenerator/api/todos/update', methods=['POST'])
def update_todo():
    """Update TODO"""
    try:
        data = request.get_json() or {}
        todo_id = data.get('todo_id')
        updates = data.get('updates', {})
        
        if not todo_id:
            return jsonify({'success': False, 'error': 'todo_id required'}), 400
        
        result = todo_system_manager.update_todo(todo_id, updates)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@todo_system_bp.route('/api/todos/complete', methods=['POST'])
@todo_system_bp.route('/vidgenerator/api/todos/complete', methods=['POST'])
def complete_todo():
    """Complete TODO"""
    try:
        data = request.get_json() or {}
        todo_id = data.get('todo_id')
        
        if not todo_id:
            return jsonify({'success': False, 'error': 'todo_id required'}), 400
        
        result = todo_system_manager.complete_todo(todo_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@todo_system_bp.route('/api/todos/start', methods=['POST'])
@todo_system_bp.route('/vidgenerator/api/todos/start', methods=['POST'])
def start_todo():
    """Start working on TODO"""
    try:
        data = request.get_json() or {}
        todo_id = data.get('todo_id')
        
        if not todo_id:
            return jsonify({'success': False, 'error': 'todo_id required'}), 400
        
        result = todo_system_manager.start_todo(todo_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@todo_system_bp.route('/api/todos/list', methods=['GET'])
@todo_system_bp.route('/vidgenerator/api/todos/list', methods=['GET'])
def list_todos():
    """List TODOs with filters"""
    try:
        status = request.args.get('status')
        priority = request.args.get('priority')
        category = request.args.get('category')
        
        status_enum = TodoStatus(status) if status else None
        priority_enum = TodoPriority(priority) if priority else None
        
        todos = todo_system_manager.get_todos(status_enum, priority_enum, category)
        
        return jsonify({
            'success': True,
            'todos': todos,
            'count': len(todos)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@todo_system_bp.route('/api/todos/statistics', methods=['GET'])
@todo_system_bp.route('/vidgenerator/api/todos/statistics', methods=['GET'])
def get_statistics():
    """Get TODO statistics"""
    try:
        stats = todo_system_manager.get_todo_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

