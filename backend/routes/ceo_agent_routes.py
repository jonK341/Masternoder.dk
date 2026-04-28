"""
CEO Agent Routes
API endpoints for CEO agent
"""
from flask import Blueprint, request, jsonify
from backend.services.ceo_agent import ceo_agent

ceo_agent_bp = Blueprint('ceo_agent', __name__)


@ceo_agent_bp.route('/api/ceo-agent/status', methods=['GET'])
def get_ceo_status():
    """Get CEO agent status"""
    try:
        status = ceo_agent.get_status()
        return jsonify({
            'success': True,
            'ceo_agent': status
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ceo_agent_bp.route('/api/ceo-agent/strategic-planning', methods=['POST'])
def strategic_planning():
    """Develop strategic plan"""
    try:
        data = request.get_json() or {}
        goal = data.get('goal')
        timeframe = data.get('timeframe', 'long-term')
        context = data.get('context', {})
        
        if not goal:
            return jsonify({
                'success': False,
                'error': 'goal is required'
            }), 400
        
        result = ceo_agent.strategic_planning(goal, timeframe, context)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ceo_agent_bp.route('/api/ceo-agent/decision', methods=['POST'])
def make_executive_decision():
    """Make executive decision"""
    try:
        data = request.get_json() or {}
        options = data.get('options', [])
        context = data.get('context', {})
        
        if not options:
            return jsonify({
                'success': False,
                'error': 'options are required'
            }), 400
        
        result = ceo_agent.make_executive_decision(options, context)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ceo_agent_bp.route('/api/ceo-agent/assess-risk', methods=['POST'])
def assess_risk():
    """Assess risk"""
    try:
        data = request.get_json() or {}
        action = data.get('action', {})
        context = data.get('context', {})
        
        result = ceo_agent.assess_risk(action, context)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ceo_agent_bp.route('/api/ceo-agent/optimize-resources', methods=['POST'])
def optimize_resources():
    """Optimize resources"""
    try:
        data = request.get_json() or {}
        resources = data.get('resources', {})
        goals = data.get('goals', [])
        
        result = ceo_agent.optimize_resources(resources, goals)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
