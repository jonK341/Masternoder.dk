"""
Agent Reengineering Routes
API endpoints for agent reengineering system
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List

agent_reengineering_bp = Blueprint('agent_reengineering', __name__)


@agent_reengineering_bp.route('/api/agent/reengineering/learn', methods=['POST'])
def learn_from_task():
    """Learn from a completed task"""
    try:
        data = request.get_json() or {}
        task_data = data.get('task_data', {})
        result_data = data.get('result_data', {})
        
        if not task_data:
            return jsonify({
                'success': False,
                'error': 'task_data is required'
            }), 400
        
        from backend.services.agent_reengineering import agent_reengineering
        
        result = agent_reengineering.learn_from_task(task_data, result_data)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_reengineering_bp.route('/api/agent/reengineering/missing-handlers', methods=['GET'])
def get_missing_handlers():
    """Get list of missing handlers that need migration"""
    try:
        from backend.services.agent_reengineering import agent_reengineering
        
        missing = agent_reengineering.get_missing_handlers()
        
        return jsonify({
            'success': True,
            'missing_handlers': missing,
            'count': len(missing)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_reengineering_bp.route('/api/agent/reengineering/create-handler', methods=['POST'])
def create_autofix_handler():
    """Create an autofix handler"""
    try:
        data = request.get_json() or {}
        handler_type = data.get('handler_type')
        context = data.get('context', {})
        
        if not handler_type:
            return jsonify({
                'success': False,
                'error': 'handler_type is required'
            }), 400
        
        from backend.services.agent_reengineering import agent_reengineering
        
        handler = agent_reengineering.create_autofix_handler(handler_type, context)
        
        return jsonify({
            'success': True,
            'handler': handler
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_reengineering_bp.route('/api/agent/reengineering/auto-create', methods=['POST'])
def auto_create_missing_handlers():
    """Automatically create handlers for missing handlers"""
    try:
        from backend.services.agent_reengineering import agent_reengineering
        
        created = agent_reengineering.auto_create_missing_handlers()
        
        return jsonify({
            'success': True,
            'handlers_created': created,
            'count': len(created)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_reengineering_bp.route('/api/agent/reengineering/stats', methods=['GET'])
def get_reengineering_stats():
    """Get reengineering statistics"""
    try:
        from backend.services.agent_reengineering import agent_reengineering
        
        stats = {
            'task_patterns_count': len(agent_reengineering.learning.get('task_patterns', {})),
            'error_patterns_count': len(agent_reengineering.learning.get('error_patterns', {})),
            'fix_patterns_count': len(agent_reengineering.learning.get('fix_patterns', {})),
            'handlers_count': len(agent_reengineering.handlers),
            'missing_handlers_count': len(agent_reengineering.get_missing_handlers()),
            'success_rates': agent_reengineering.learning.get('success_rate', {})
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
