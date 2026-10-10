"""
Progress Tracking API
Server-side progress tracking and synchronization
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import json
import os

progress_api_bp = Blueprint('progress_api', __name__)

PROGRESS_FILE = '/var/www/html/vidgenerator/progress_data.json'

def load_progress_data():
    """Load progress data from file"""
    try:
        if os.path.exists(PROGRESS_FILE):
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'todos': [], 'stats': {}, 'last_updated': None}
    except Exception as e:
        print(f"[ProgressAPI] Error loading progress data: {e}")
        return {'todos': [], 'stats': {}, 'last_updated': None}

def save_progress_data(data):
    """Save progress data to file"""
    try:
        data['last_updated'] = datetime.now().isoformat()
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[ProgressAPI] Error saving progress data: {e}")
        return False

@progress_api_bp.route('/api/progress/sync', methods=['POST'])
def sync_progress():
    """Sync progress data with server"""
    try:
        data = request.get_json()
        todos = data.get('todos', [])
        stats = data.get('stats', {})
        
        # Load existing data
        existing_data = load_progress_data()
        
        # Merge todos (server takes precedence for conflicts)
        existing_todos = {t['id']: t for t in existing_data.get('todos', [])}
        for todo in todos:
            if todo['id'] in existing_todos:
                # Update if server version is newer
                existing_todo = existing_todos[todo['id']]
                if existing_todo.get('updatedAt', '') > todo.get('updatedAt', ''):
                    todos.remove(todo)
                    todos.append(existing_todo)
            else:
                existing_todos[todo['id']] = todo
        
        # Save merged data
        progress_data = {
            'todos': list(existing_todos.values()),
            'stats': stats,
            'last_updated': datetime.now().isoformat()
        }
        
        save_progress_data(progress_data)
        
        return jsonify({
            'success': True,
            'todos': progress_data['todos'],
            'stats': progress_data['stats']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_api_bp.route('/api/progress/get', methods=['GET'])
def get_progress():
    """Get current progress data"""
    try:
        data = load_progress_data()
        return jsonify({
            'success': True,
            'todos': data.get('todos', []),
            'stats': data.get('stats', {}),
            'last_updated': data.get('last_updated')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@progress_api_bp.route('/api/progress/update', methods=['POST'])
def update_progress():
    """Update a specific task"""
    try:
        data = request.get_json()
        task_id = data.get('task_id')
        new_status = data.get('status')
        
        if not task_id or not new_status:
            return jsonify({
                'success': False,
                'error': 'task_id and status are required'
            }), 400
        
        progress_data = load_progress_data()
        todos = progress_data.get('todos', [])
        
        # Find and update task
        updated = False
        for todo in todos:
            if todo['id'] == task_id:
                todo['status'] = new_status
                todo['updatedAt'] = datetime.now().isoformat()
                updated = True
                break
        
        if updated:
            save_progress_data(progress_data)
            return jsonify({
                'success': True,
                'todo': next((t for t in todos if t['id'] == task_id), None)
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

