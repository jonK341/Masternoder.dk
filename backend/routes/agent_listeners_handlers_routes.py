"""
Agent Event Listeners and Error Handlers Routes
Licensed from Law Paragraph System
"""
from flask import Blueprint, request, jsonify
from backend.services.agent_listeners_handlers_system import agent_listeners_handlers
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

agent_listeners_bp = Blueprint('agent_listeners', __name__)


@agent_listeners_bp.route('/api/agent/<agent_id>/attach-listeners', methods=['POST'])
@agent_listeners_bp.route('/vidgenerator/api/agent/<agent_id>/attach-listeners', methods=['POST'])
@rate_limit()
def attach_listeners(agent_id: str):
    """Attach all event listeners to an agent"""
    try:
        result = agent_listeners_handlers.attach_listeners_to_agent(agent_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@agent_listeners_bp.route('/api/agent/<agent_id>/attach-handlers', methods=['POST'])
@agent_listeners_bp.route('/vidgenerator/api/agent/<agent_id>/attach-handlers', methods=['POST'])
@rate_limit()
def attach_handlers(agent_id: str):
    """Attach all error handlers to an agent"""
    try:
        result = agent_listeners_handlers.attach_handlers_to_agent(agent_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@agent_listeners_bp.route('/api/agent/<agent_id>/listeners')
@agent_listeners_bp.route('/vidgenerator/api/agent/<agent_id>/listeners')
@rate_limit()
def get_listeners(agent_id: str):
    """Get all listeners for an agent"""
    try:
        result = agent_listeners_handlers.get_agent_listeners(agent_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@agent_listeners_bp.route('/api/agent/<agent_id>/handlers')
@agent_listeners_bp.route('/vidgenerator/api/agent/<agent_id>/handlers')
@rate_limit()
def get_handlers(agent_id: str):
    """Get all handlers for an agent"""
    try:
        result = agent_listeners_handlers.get_agent_handlers(agent_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@agent_listeners_bp.route('/api/agent/<agent_id>/cv')
@agent_listeners_bp.route('/vidgenerator/api/agent/<agent_id>/cv')
@rate_limit()
def get_agent_cv(agent_id: str):
    """Get complete agent CV including listeners and handlers"""
    try:
        result = agent_listeners_handlers.get_agent_cv(agent_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@agent_listeners_bp.route('/api/agent/listeners/types')
@agent_listeners_bp.route('/vidgenerator/api/agent/listeners/types')
@rate_limit()
def get_listener_types():
    """Get all available listener types"""
    return jsonify({
        'success': True,
        'listener_types': agent_listeners_handlers.EVENT_LISTENER_TYPES
    }), 200


@agent_listeners_bp.route('/api/agent/handlers/types')
@agent_listeners_bp.route('/vidgenerator/api/agent/handlers/types')
@rate_limit()
def get_handler_types():
    """Get all available handler types"""
    return jsonify({
        'success': True,
        'handler_types': agent_listeners_handlers.ERROR_HANDLER_TYPES
    }), 200

