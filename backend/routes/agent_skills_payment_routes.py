"""
Agent Skills Payment Routes
API endpoints for agent skill sets, working hours, and payment
"""
from flask import Blueprint, request, jsonify
from backend.services.agent_skills_payment_system import agent_skills_payment_system
from src.utils.rate_limiter import rate_limit
import sys

agent_skills_payment_bp = Blueprint('agent_skills_payment', __name__)

@agent_skills_payment_bp.route('/api/agent-skills-payment/assign-skills', methods=['POST'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/assign-skills', methods=['POST'])
@rate_limit()
def assign_skill_set():
    """Assign a skill set to an agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        skill_set = data.get('skill_set', [])
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        if not skill_set:
            return jsonify({
                'success': False,
                'error': 'skill_set required'
            }), 400
        
        result = agent_skills_payment_system.assign_skill_set(agent_id, skill_set)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        print(f"[AgentSkillsPayment] Error assigning skills: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/set-working-hours', methods=['POST'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/set-working-hours', methods=['POST'])
@rate_limit()
def set_working_hours():
    """Set working hours for an agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        preset = data.get('preset', 'full_time')
        custom_hours = data.get('custom_hours')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_skills_payment_system.set_working_hours(agent_id, preset, custom_hours)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/track-hours', methods=['POST'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/track-hours', methods=['POST'])
@rate_limit()
def track_work_hours():
    """Track hours worked by an agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        date = data.get('date')
        hours = data.get('hours', 0.0)
        is_overtime = data.get('is_overtime', False)
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        if not date:
            from datetime import datetime
            date = datetime.utcnow().strftime('%Y-%m-%d')
        
        result = agent_skills_payment_system.track_work_hours(agent_id, date, hours, is_overtime)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/calculate-payment', methods=['GET'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/calculate-payment', methods=['GET'])
@rate_limit()
def calculate_payment():
    """Calculate payment for an agent"""
    try:
        agent_id = request.args.get('agent_id')
        date = request.args.get('date')
        period = request.args.get('period', 'daily')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_skills_payment_system.calculate_payment(agent_id, date, period)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/process-payment', methods=['POST'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/process-payment', methods=['POST'])
@rate_limit()
def process_payment():
    """Process payment and award points"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        period = data.get('period', 'daily')
        date = data.get('date')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_skills_payment_system.process_payment(agent_id, period, date)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/summary/<agent_id>', methods=['GET'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/summary/<agent_id>', methods=['GET'])
@rate_limit()
def get_payment_summary(agent_id):
    """Get payment summary for an agent"""
    try:
        result = agent_skills_payment_system.get_agent_payment_summary(agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/skill-categories', methods=['GET'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/skill-categories', methods=['GET'])
@rate_limit()
def get_skill_categories():
    """Get all skill categories"""
    try:
        result = agent_skills_payment_system.get_all_skill_categories()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_skills_payment_bp.route('/api/agent-skills-payment/working-hours-presets', methods=['GET'])
@agent_skills_payment_bp.route('/vidgenerator/api/agent-skills-payment/working-hours-presets', methods=['GET'])
@rate_limit()
def get_working_hours_presets():
    """Get all working hours presets"""
    try:
        result = agent_skills_payment_system.get_all_working_hours_presets()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
