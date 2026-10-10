"""
Enhanced Trophy Hunter Routes - Intelligence, Reactions, Rewards, Magic
"""
from flask import Blueprint, request, jsonify
from backend.services.trophy_system import trophy_system
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import json

trophy_hunter_enhanced_bp = Blueprint('trophy_hunter_enhanced', __name__)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/intelligence/store', methods=['POST'])
@rate_limit
def store_intelligence():
    """Store intelligence and functions"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        intelligence_type = InputValidator.sanitize_string(data.get('intelligence_type', ''))
        intelligence_data = data.get('data', {})
        
        if not intelligence_type:
            return jsonify({'success': False, 'error': 'intelligence_type required'}), 400
        
        trophy_system.store_intelligence(user_id, intelligence_type, intelligence_data)
        
        return jsonify({
            'success': True,
            'message': 'Intelligence stored successfully'
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/intelligence', methods=['GET'])
def get_intelligence():
    """Get stored intelligence"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        intelligence = trophy_system.get_intelligence(user_id)
        
        return jsonify({
            'success': True,
            'intelligence': intelligence
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/reaction/increment', methods=['POST'])
@rate_limit
def increment_reaction():
    """Increment reaction counter"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        reaction_type = InputValidator.sanitize_string(data.get('reaction_type', 'general'))
        points = int(data.get('points', 1))
        
        result = trophy_system.increment_reaction_counter(user_id, reaction_type, points)
        
        return jsonify({
            'success': True,
            'reaction': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/reaction', methods=['GET'])
def get_reaction_counter():
    """Get reaction counter stats"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        reaction_type = request.args.get('reaction_type')
        
        result = trophy_system.get_reaction_counter(user_id, reaction_type)
        
        return jsonify({
            'success': True,
            'reactions': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/stats/link', methods=['POST'])
@rate_limit
def link_stats_and_points():
    """Link stats and point scores together"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        stats_update = data.get('stats_update', {})
        
        result = trophy_system.link_stats_and_points(user_id, stats_update)
        
        return jsonify({
            'success': True,
            'linked_stats': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/reward/award', methods=['POST'])
@rate_limit
def award_reward():
    """Award reward under Trophy Hunter"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        reward_type = InputValidator.sanitize_string(data.get('reward_type', ''))
        reward_data = data.get('reward_data', {})
        
        if not reward_type:
            return jsonify({'success': False, 'error': 'reward_type required'}), 400
        
        reward = trophy_system.award_reward(user_id, reward_type, reward_data)
        
        return jsonify({
            'success': True,
            'reward': reward
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/rewards', methods=['GET'])
def get_rewards():
    """Get all rewards for user"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        rewards = trophy_system.get_rewards(user_id)
        
        return jsonify({
            'success': True,
            'rewards': rewards
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/unemotional-world/increase', methods=['POST'])
@rate_limit
def increase_unemotional_acceptance():
    """Increase UnEmotional World acceptance"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        amount = float(data.get('amount', 0.1))
        
        result = trophy_system.increase_unemotional_world_acceptance(user_id, amount)
        
        return jsonify({
            'success': True,
            'acceptance': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/unemotional-world', methods=['GET'])
def get_unemotional_acceptance():
    """Get UnEmotional World acceptance"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        result = trophy_system.get_unemotional_world_acceptance(user_id)
        
        return jsonify({
            'success': True,
            'acceptance': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/3d-glasses/activate', methods=['POST'])
@rate_limit
def activate_3d_glasses():
    """Activate 3D glasses"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        enabled = data.get('enabled', True)
        
        result = trophy_system.activate_3d_glasses(user_id, enabled)
        
        return jsonify({
            'success': True,
            'glasses': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/3d-glasses/counter', methods=['POST'])
@rate_limit
def track_counter_3d():
    """Track counter with 3D glasses"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        counter_name = InputValidator.sanitize_string(data.get('counter_name', ''))
        value = int(data.get('value', 1))
        
        if not counter_name:
            return jsonify({'success': False, 'error': 'counter_name required'}), 400
        
        result = trophy_system.track_counter_with_3d(user_id, counter_name, value)
        
        return jsonify({
            'success': True,
            'counter': result
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/counter-spell/add', methods=['POST'])
@rate_limit
def add_counter_spell():
    """Add CounterSpell"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        spell_name = InputValidator.sanitize_string(data.get('spell_name', ''))
        spell_data = data.get('spell_data', {})
        
        if not spell_name:
            return jsonify({'success': False, 'error': 'spell_name required'}), 400
        
        spell = trophy_system.add_counter_spell(user_id, spell_name, spell_data)
        
        return jsonify({
            'success': True,
            'spell': spell
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/interrupt-spell/add', methods=['POST'])
@rate_limit
def add_interrupt_spell():
    """Add Interrupt Spell"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        spell_name = InputValidator.sanitize_string(data.get('spell_name', ''))
        spell_data = data.get('spell_data', {})
        
        if not spell_name:
            return jsonify({'success': False, 'error': 'spell_name required'}), 400
        
        spell = trophy_system.add_interrupt_spell(user_id, spell_name, spell_data)
        
        return jsonify({
            'success': True,
            'spell': spell
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@trophy_hunter_enhanced_bp.route('/api/trophy-hunter/magi', methods=['GET'])
def get_magi_system():
    """Get magic system data"""
    try:
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'))
        
        magi = trophy_system.get_magi_system(user_id)
        
        return jsonify({
            'success': True,
            'magi': magi
        }), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


