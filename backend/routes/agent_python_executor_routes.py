"""
Agent Python Executor Routes
API endpoints for Python execution
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_python_executor import agent_python_executor

agent_python_executor_bp = Blueprint('agent_python_executor', __name__)

@agent_python_executor_bp.route('/api/agent/python/execute-file', methods=['POST'])
def execute_python_file():
    """Execute a Python file"""
    try:
        data = request.get_json() or {}
        file_path = data.get('file_path')
        args = data.get('args', [])
        timeout = data.get('timeout', 300)
        
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path required'
            }), 400
        
        result = agent_python_executor.execute_python_file(file_path, args, timeout)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_python_executor_bp.route('/api/agent/python/execute-code', methods=['POST'])
def execute_python_code():
    """Execute Python code"""
    try:
        data = request.get_json() or {}
        code = data.get('code')
        timeout = data.get('timeout', 60)
        
        if not code:
            return jsonify({
                'success': False,
                'error': 'code required'
            }), 400
        
        result = agent_python_executor.execute_python_code(code, timeout)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_python_executor_bp.route('/api/agent/python/scripts', methods=['GET'])
def list_scripts():
    """List available Python scripts"""
    try:
        directory = request.args.get('directory')
        result = agent_python_executor.list_available_scripts(directory)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_python_executor_bp.route('/api/agent/python/script-info', methods=['GET'])
def get_script_info():
    """Get information about a Python script"""
    try:
        file_path = request.args.get('file_path')
        if not file_path:
            return jsonify({
                'success': False,
                'error': 'file_path required'
            }), 400
        
        result = agent_python_executor.get_script_info(file_path)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_python_executor_bp.route('/api/agent/python/history', methods=['GET'])
def get_execution_history():
    """Get execution history"""
    try:
        limit = int(request.args.get('limit', 50))
        result = agent_python_executor.get_execution_history(limit)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
