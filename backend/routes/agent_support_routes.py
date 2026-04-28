"""
Agent Support Routes
API endpoints for support and service management
"""
from flask import Blueprint, jsonify, request
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.services.agent_support_service import agent_support_service

agent_support_bp = Blueprint('agent_support', __name__)

@agent_support_bp.route('/api/agent/support/tickets', methods=['GET', 'POST'])
def support_tickets():
    """Get or create support tickets"""
    try:
        if request.method == 'GET':
            status = request.args.get('status')
            result = agent_support_service.get_support_tickets(status)
            return jsonify(result), 200
        else:
            # POST - Create ticket
            data = request.get_json() or {}
            result = agent_support_service.create_support_ticket(
                data.get('title', 'Support Ticket'),
                data.get('description', ''),
                data.get('priority', 'medium')
            )
            return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/tickets/<ticket_id>/resolve', methods=['POST'])
def resolve_ticket(ticket_id):
    """Resolve a support ticket"""
    try:
        result = agent_support_service.resolve_ticket(ticket_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/services', methods=['GET'])
def get_services():
    """Get all services"""
    try:
        result = agent_support_service.get_services()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/services/<service_id>', methods=['GET'])
def get_service(service_id):
    """Get a specific service"""
    try:
        result = agent_support_service.get_service(service_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/resources', methods=['GET'])
def get_support_resources():
    """Get support resources"""
    try:
        result = agent_support_service.get_support_resources()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== TRIGGER ENDPOINTS ==========

@agent_support_bp.route('/api/agent/support/triggers', methods=['GET'])
def get_triggers():
    """Get all triggers"""
    try:
        from backend.services.agent_trigger_system import agent_trigger_system
        triggers = agent_trigger_system.triggers.get('triggers', [])
        return jsonify({
            'success': True,
            'triggers': triggers,
            'count': len(triggers)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/triggers/stats', methods=['GET'])
def get_triggers_stats():
    """Get trigger statistics"""
    try:
        from backend.services.agent_trigger_system import agent_trigger_system
        result = agent_trigger_system.get_trigger_stats()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== ACTIVATION ENDPOINTS ==========

@agent_support_bp.route('/api/agent/support/activation/status', methods=['GET'])
def get_activation_status():
    """Get activation system status"""
    try:
        from backend.services.agent_activation_system import agent_activation_system
        result = agent_activation_system.get_status()
        activations = agent_activation_system.activations.get('auto_activations', [])
        return jsonify({
            'success': True,
            'status': result,
            'activations': activations
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/activation/start', methods=['POST'])
def start_activation_system():
    """Start activation system"""
    try:
        from backend.services.agent_activation_system import agent_activation_system
        agent_activation_system.start()
        return jsonify({
            'success': True,
            'message': 'Activation system started'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_support_bp.route('/api/agent/support/triggers/award', methods=['POST'])
def award_trigger():
    """Award points via trigger"""
    try:
        from backend.services.agent_trigger_system import agent_trigger_system
        data = request.get_json() or {}
        trigger_id = data.get('trigger_id')
        user_id = data.get('user_id', 'agent_user')
        metadata = data.get('metadata', {})
        
        if not trigger_id:
            return jsonify({
                'success': False,
                'error': 'trigger_id required'
            }), 400
        
        result = agent_trigger_system.award_points(trigger_id, user_id, metadata)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500