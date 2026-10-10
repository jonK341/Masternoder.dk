"""
178 Systems Knowledge & Intelligence Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.178_systems_knowledge_intelligence import systems_178_knowledge_intelligence
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

knowledge_intelligence_bp = Blueprint('knowledge_intelligence', __name__)

def get_user_id():
    """Get user ID from session or request"""
    from flask import session
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session.get('user_id', request.args.get('user_id', 'anonymous'))


@knowledge_intelligence_bp.route('/api/178-systems/knowledge/<system_id>')
@knowledge_intelligence_bp.route('/vidgenerator/api/178-systems/knowledge/<system_id>')
@rate_limit()
def get_system_knowledge(system_id: str):
    """Get knowledge for a system"""
    try:
        result = systems_178_knowledge_intelligence.get_system_knowledge(system_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@knowledge_intelligence_bp.route('/api/178-systems/intelligence/<system_id>')
@knowledge_intelligence_bp.route('/vidgenerator/api/178-systems/intelligence/<system_id>')
@rate_limit()
def get_system_intelligence(system_id: str):
    """Get intelligence for a user's system"""
    try:
        user_id = get_user_id()
        result = systems_178_knowledge_intelligence.get_system_intelligence(system_id, user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@knowledge_intelligence_bp.route('/api/178-systems/intelligence/<system_id>', methods=['POST'])
@knowledge_intelligence_bp.route('/vidgenerator/api/178-systems/intelligence/<system_id>', methods=['POST'])
@rate_limit()
def update_intelligence(system_id: str):
    """Update intelligence data"""
    try:
        user_id = get_user_id()
        data = request.get_json() or {}
        
        result = systems_178_knowledge_intelligence.update_intelligence(
            system_id, user_id, data
        )
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@knowledge_intelligence_bp.route('/api/178-systems/knowledge/all')
@knowledge_intelligence_bp.route('/vidgenerator/api/178-systems/knowledge/all')
@rate_limit()
def get_all_knowledge():
    """Get knowledge for all systems"""
    try:
        result = systems_178_knowledge_intelligence.get_all_systems_knowledge()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

