"""
Agent Error Handler Routes
API endpoints for agent error handling and use case generation
"""
from flask import Blueprint, jsonify, request
from backend.services.agent_error_handler import agent_error_handler

agent_error_handler_bp = Blueprint('agent_error_handler', __name__)

# ========== ERROR CAPTURE ENDPOINTS ==========

@agent_error_handler_bp.route('/api/agent/error-handler/capture', methods=['POST'])
def capture_error():
    """Capture an error"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id', 'system')
        error_type = data.get('error_type', 'UNKNOWN')
        error_message = data.get('error_message', '')
        context = data.get('context', {})
        stack_trace = data.get('stack_trace')
        
        if not error_message:
            return jsonify({
                'success': False,
                'error': 'error_message required'
            }), 400
        
        error_entry = agent_error_handler.capture_error(
            agent_id=agent_id,
            error_type=error_type,
            error_message=error_message,
            context=context,
            stack_trace=stack_trace
        )
        
        return jsonify({
            'success': True,
            'error': error_entry
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== LOG ANALYSIS ENDPOINTS ==========

@agent_error_handler_bp.route('/api/agent/error-handler/analyze-log', methods=['POST'])
def analyze_log_file():
    """Analyze a log file for errors"""
    try:
        data = request.get_json() or {}
        log_file_path = data.get('log_file_path')
        agent_id = data.get('agent_id', 'system')
        
        if not log_file_path:
            return jsonify({
                'success': False,
                'error': 'log_file_path required'
            }), 400
        
        result = agent_error_handler.analyze_log_file(log_file_path, agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_error_handler_bp.route('/api/agent/error-handler/analyze-log-dir', methods=['POST'])
def analyze_log_directory():
    """Analyze all log files in a directory"""
    try:
        data = request.get_json() or {}
        log_dir = data.get('log_dir')
        agent_id = data.get('agent_id', 'system')
        
        if not log_dir:
            return jsonify({
                'success': False,
                'error': 'log_dir required'
            }), 400
        
        result = agent_error_handler.analyze_log_directory(log_dir, agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== USE CASE GENERATION ENDPOINTS ==========

@agent_error_handler_bp.route('/api/agent/error-handler/generate-use-case', methods=['POST'])
def generate_use_case():
    """Generate an AI-powered use case from an error"""
    try:
        data = request.get_json() or {}
        error_id = data.get('error_id')
        agent_id = data.get('agent_id', 'ai_agent')
        
        if not error_id:
            return jsonify({
                'success': False,
                'error': 'error_id required'
            }), 400
        
        result = agent_error_handler.generate_use_case_from_error(error_id, agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== QUERY ENDPOINTS ==========

@agent_error_handler_bp.route('/api/agent/error-handler/errors', methods=['GET'])
def get_errors():
    """Get errors with filters"""
    try:
        agent_id = request.args.get('agent_id')
        status = request.args.get('status')
        category = request.args.get('category')
        limit = int(request.args.get('limit', 100))
        
        errors = agent_error_handler.get_errors(agent_id, status, category, limit)
        return jsonify({
            'success': True,
            'errors': errors,
            'count': len(errors)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_error_handler_bp.route('/api/agent/error-handler/use-cases', methods=['GET'])
def get_use_cases():
    """Get use cases with filters"""
    try:
        error_id = request.args.get('error_id')
        agent_id = request.args.get('agent_id')
        status = request.args.get('status')
        limit = int(request.args.get('limit', 100))
        
        use_cases = agent_error_handler.get_use_cases(error_id, agent_id, status, limit)
        return jsonify({
            'success': True,
            'use_cases': use_cases,
            'count': len(use_cases)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_error_handler_bp.route('/api/agent/error-handler/statistics', methods=['GET'])
def get_error_statistics():
    """Get error statistics"""
    try:
        stats = agent_error_handler.get_error_statistics()
        return jsonify({
            'success': True,
            'statistics': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_error_handler_bp.route('/api/agent/error-handler/error/<error_id>', methods=['GET'])
def get_error(error_id):
    """Get a specific error"""
    try:
        errors = agent_error_handler.get_errors()
        error = next((e for e in errors if e['id'] == error_id), None)
        
        if not error:
            return jsonify({
                'success': False,
                'error': 'Error not found'
            }), 404
        
        return jsonify({
            'success': True,
            'error': error
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_error_handler_bp.route('/api/agent/error-handler/use-case/<use_case_id>', methods=['GET'])
def get_use_case(use_case_id):
    """Get a specific use case"""
    try:
        use_cases = agent_error_handler.get_use_cases()
        use_case = next((uc for uc in use_cases if uc['id'] == use_case_id), None)
        
        if not use_case:
            return jsonify({
                'success': False,
                'error': 'Use case not found'
            }), 404
        
        return jsonify({
            'success': True,
            'use_case': use_case
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== RESOLUTION ENDPOINTS ==========

@agent_error_handler_bp.route('/api/agent/error-handler/resolve/<error_id>', methods=['POST'])
def resolve_error(error_id):
    """Mark an error as resolved"""
    try:
        data = request.get_json() or {}
        resolution_notes = data.get('resolution_notes', '')
        
        result = agent_error_handler.resolve_error(error_id, resolution_notes)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
