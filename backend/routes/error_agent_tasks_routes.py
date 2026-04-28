"""
Error Agent Tasks Routes
Generate and assign error migration tasks to agents
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Dict, List
import os
import glob
import re

error_agent_tasks_bp = Blueprint('error_agent_tasks', __name__)

# Base directory for finding JavaScript files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@error_agent_tasks_bp.route('/api/errors/tasks/generate', methods=['POST'])
def generate_migration_tasks():
    """
    Generate migration tasks from error handler analysis
    Returns list of tasks that can be assigned to agents
    """
    try:
        data = request.get_json() or {}
        priority_filter = data.get('priority', 'all')  # 'high', 'medium', 'low', 'all'
        max_tasks = data.get('max_tasks', 10)
        
        # Get error handler analysis
        from backend.routes.error_handler_status_routes import analyze_error_handlers
        analysis = analyze_error_handlers()
        
        if not analysis.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to analyze error handlers'
            }), 500
        
        files_needing_migration = analysis.get('analysis', {}).get('top_files_needing_migration', [])
        
        # Generate tasks
        tasks = []
        for idx, file_info in enumerate(files_needing_migration[:max_tasks]):
            file_name = file_info.get('name', '')
            handlers = file_info.get('handlers', 0)
            
            # Determine priority
            if handlers >= 30:
                priority = 'high'
            elif handlers >= 15:
                priority = 'medium'
            else:
                priority = 'low'
            
            # Filter by priority if specified
            if priority_filter != 'all' and priority != priority_filter:
                continue
            
            task = {
                'task_id': f"migrate_error_handlers_{idx + 1:03d}",
                'task_type': 'file_migration',
                'file_name': file_name,
                'handlers_count': handlers,
                'priority': priority,
                'estimated_time': f"{handlers * 2} minutes",
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'skills_required': ['code_analysis', 'error_handling', 'javascript'],
                'instructions': [
                    f"1. Analyze error handlers in {file_name}",
                    "2. Replace console.error/console.warn with ErrorManager.logError()",
                    "3. Replace try-catch blocks with ErrorManager.wrap() where appropriate",
                    "4. Test all error paths",
                    "5. Verify ErrorManager integration",
                    "6. Remove old error handling code"
                ],
                'completion_criteria': [
                    f"All {handlers} error handlers use ErrorManager",
                    "No console.error/console.warn remain",
                    "All tests pass",
                    "ErrorManager logs errors correctly"
                ],
                'points_reward': {
                    'xp': handlers * 5,  # ENHANCED: 5 XP per handler migrated (was 2)
                    'activity_points': handlers * 2,  # ENHANCED: 2 activity points per handler (was 1)
                    'generation_points': handlers  # NEW: 1 generation point per handler
                }
            }
            tasks.append(task)
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'total_tasks': len(tasks),
            'total_handlers': sum(t['handlers_count'] for t in tasks)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@error_agent_tasks_bp.route('/api/errors/tasks/assign', methods=['POST'])
def assign_migration_task():
    """
    Assign a migration task to an agent
    """
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        agent_id = data.get('agent_id', 'agent_manager')  # Default to manager
        
        if not task_id:
            return jsonify({
                'success': False,
                'error': 'task_id is required'
            }), 400
        
        # Generate task details if not provided
        if 'task' not in data:
            # Extract file name from task_id (format: migrate_error_handlers_001)
            # Get task details from analysis
            from backend.routes.error_handler_status_routes import analyze_error_handlers
            analysis = analyze_error_handlers()
            if analysis.get('success'):
                files = analysis.get('analysis', {}).get('top_files_needing_migration', [])
                task_num = int(task_id.split('_')[-1]) - 1
                if 0 <= task_num < len(files):
                    file_info = files[task_num]
                    task_description = f"Migrate {file_info.get('handlers', 0)} error handlers in {file_info.get('name', '')}"
                    handlers_count = file_info.get('handlers', 0)
                else:
                    task_description = f"Migrate error handlers for task {task_id}"
                    handlers_count = 0
            else:
                task_description = f"Migrate error handlers for task {task_id}"
                handlers_count = 0
        else:
            task_description = data.get('task')
            handlers_count = data.get('handlers_count', 0)
        
        # Assign task via agent manager with fallback
        try:
            from backend.services.agent_manager import agent_manager
            from backend.services.agent_point_creator import agent_point_creator
            
            if agent_manager:
                result = agent_manager.assign_task(
                    agent_id=agent_id,
                    task=task_description,
                    priority=data.get('priority', 'medium')
                )
            else:
                result = {'success': True, 'status': 'queued', 'note': 'Agent manager unavailable'}
            
            # Award points for task assignment with fallback
            points_awarded = False
            if result.get('success') and agent_point_creator:
                try:
                    agent_point_creator.award_points_for_agent_action(
                        agent_id=agent_id,
                        action='accept_migration_task',
                        user_id='system',
                        points={'xp': 25, 'activity_points': 10, 'generation_points': 5}  # ENHANCED
                    )
                    points_awarded = True
                except Exception as e:
                    print(f"[WARN] Could not award points: {e}")
            
            return jsonify({
                'success': True,
                'task_id': task_id,
                'agent_id': agent_id,
                'result': result,
                'points_awarded': points_awarded,
                'points': {'xp': 25, 'activity_points': 10, 'generation_points': 5}  # ENHANCED
            }), 200
        except (ImportError, Exception) as e:
            # Fallback if imports fail
            return jsonify({
                'success': True,
                'task_id': task_id,
                'agent_id': agent_id,
                'result': {'success': True, 'status': 'queued', 'note': f'Service unavailable: {str(e)}'},
                'points_awarded': False,
                'points': {'xp': 25, 'activity_points': 10, 'generation_points': 5}  # ENHANCED
            }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@error_agent_tasks_bp.route('/api/errors/tasks/complete', methods=['POST'])
def complete_migration_task():
    """
    Mark a migration task as complete and award points
    """
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        agent_id = data.get('agent_id')
        handlers_migrated = data.get('handlers_migrated', 0)
        
        if not task_id or not agent_id:
            return jsonify({
                'success': False,
                'error': 'task_id and agent_id are required'
            }), 400
        
        # Award points for task completion with fallback
        try:
            from backend.services.agent_point_creator import agent_point_creator
            
            # Calculate points: 2 XP per handler + 1 activity point per handler
            points = {
                'xp': handlers_migrated * 2,
                'activity_points': handlers_migrated
            }
            
            if agent_point_creator:
                try:
                    result = agent_point_creator.award_points_for_agent_action(
                        agent_id=agent_id,
                        action='complete_migration_task',
                        user_id='system',
                        points=points
                    )
                except Exception as e:
                    print(f"[WARN] Could not award points: {e}")
                    result = {'points_awarded': points, 'note': 'Point creator unavailable'}
            else:
                result = {'points_awarded': points, 'note': 'Point creator service not available'}
        except (ImportError, Exception) as e:
            # Fallback if import fails
            points = {
                'xp': handlers_migrated * 2,
                'activity_points': handlers_migrated
            }
            result = {'points_awarded': points, 'note': f'Service unavailable: {str(e)}'}
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'agent_id': agent_id,
            'handlers_migrated': handlers_migrated,
            'points_awarded': points,
            'result': result
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@error_agent_tasks_bp.route('/api/errors/tasks/list', methods=['GET'])
def list_migration_tasks():
    """
    List available migration tasks
    """
    try:
        priority = request.args.get('priority', 'all')
        max_tasks = int(request.args.get('max_tasks', 20))
        
        # Call generate_migration_tasks logic directly
        from backend.routes.error_handler_status_routes import analyze_error_handlers
        analysis = analyze_error_handlers()
        
        if not analysis.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to analyze error handlers'
            }), 500
        
        files_needing_migration = analysis.get('analysis', {}).get('top_files_needing_migration', [])
        
        # Generate tasks
        tasks = []
        for idx, file_info in enumerate(files_needing_migration[:max_tasks]):
            file_name = file_info.get('name', '')
            handlers = file_info.get('handlers', 0)
            
            # Determine priority
            if handlers >= 30:
                task_priority = 'high'
            elif handlers >= 15:
                task_priority = 'medium'
            else:
                task_priority = 'low'
            
            # Filter by priority if specified
            if priority != 'all' and task_priority != priority:
                continue
            
            task = {
                'task_id': f"migrate_error_handlers_{idx + 1:03d}",
                'task_type': 'file_migration',
                'file_name': file_name,
                'handlers_count': handlers,
                'priority': task_priority,
                'estimated_time': f"{handlers * 2} minutes",
                'status': 'pending',
                'points_reward': {
                    'xp': handlers * 2,
                    'activity_points': handlers
                }
            }
            tasks.append(task)
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'total_tasks': len(tasks)
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@error_agent_tasks_bp.route('/api/errors/tasks/stats', methods=['GET'])
def get_task_stats():
    """
    Get statistics about migration tasks
    """
    try:
        # Get error handler analysis
        try:
            from backend.routes.error_handler_status_routes import analyze_error_handlers
            analysis = analyze_error_handlers()
        except Exception as import_error:
            # Fallback if import fails
            return jsonify({
                'success': True,
                'stats': {
                    'total_files': 0,
                    'files_migrated': 0,
                    'files_remaining': 0,
                    'migration_percent': 0,
                    'total_handlers': 0,
                    'tasks_available': {
                        'high_priority': 0,
                        'medium_priority': 0,
                        'low_priority': 0,
                        'total': 0
                    },
                    'estimated_time': {
                        'high_priority': '0 minutes',
                        'medium_priority': '0 minutes',
                        'low_priority': '0 minutes',
                        'total': '0 minutes'
                    },
                    'potential_points': {
                        'xp': 0,
                        'activity_points': 0
                    }
                },
                'note': f'Analysis unavailable: {str(import_error)}'
            }), 200
        
        if not analysis.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to analyze error handlers'
            }), 500
        
        analysis_data = analysis.get('analysis', {})
        
        total_files = analysis_data.get('total_files', 0)
        files_with_error_manager = analysis_data.get('files_with_error_manager', 0)
        files_needing_migration = analysis_data.get('files_without_error_manager', 0)
        total_handlers = analysis_data.get('total_handlers', 0)
        
        migration_percent = (files_with_error_manager / total_files * 100) if total_files > 0 else 0
        
        # Calculate task estimates
        high_priority = sum(1 for f in analysis_data.get('top_files_needing_migration', []) if f.get('handlers', 0) >= 30)
        medium_priority = sum(1 for f in analysis_data.get('top_files_needing_migration', []) if 15 <= f.get('handlers', 0) < 30)
        low_priority = sum(1 for f in analysis_data.get('top_files_needing_migration', []) if f.get('handlers', 0) < 15)
        
        # Calculate total potential points
        total_potential_xp = sum(f.get('handlers', 0) * 2 for f in analysis_data.get('top_files_needing_migration', []))
        total_potential_activity = sum(f.get('handlers', 0) for f in analysis_data.get('top_files_needing_migration', []))
        
        return jsonify({
            'success': True,
            'stats': {
                'total_files': total_files,
                'files_migrated': files_with_error_manager,
                'files_remaining': files_needing_migration,
                'migration_percent': round(migration_percent, 1),
                'total_handlers': total_handlers,
                'tasks_available': {
                    'high_priority': high_priority,
                    'medium_priority': medium_priority,
                    'low_priority': low_priority,
                    'total': high_priority + medium_priority + low_priority
                },
                'estimated_time': {
                    'high_priority': f"{sum(f.get('handlers', 0) * 2 for f in analysis_data.get('top_files_needing_migration', []) if f.get('handlers', 0) >= 30)} minutes",
                    'medium_priority': f"{sum(f.get('handlers', 0) * 2 for f in analysis_data.get('top_files_needing_migration', []) if 15 <= f.get('handlers', 0) < 30)} minutes",
                    'total': f"{sum(f.get('handlers', 0) * 2 for f in analysis_data.get('top_files_needing_migration', []))} minutes"
                },
                'potential_points': {
                    'total_xp': total_potential_xp,
                    'total_activity_points': total_potential_activity,
                    'per_handler': {'xp': 2, 'activity_points': 1}
                }
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
