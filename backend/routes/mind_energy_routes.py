"""
Mind Energy Routes - HP/Mana style energy for generators
"""
from flask import Blueprint, request, jsonify
from backend.services.mind_energy_system import mind_energy_system
from src.utils.rate_limiter import rate_limit
import sys

mind_energy_bp = Blueprint('mind_energy', __name__)

@mind_energy_bp.route('/api/mind-energy/get', methods=['GET'])
@mind_energy_bp.route('/vidgenerator/api/mind-energy/get', methods=['GET'])
@rate_limit()
def get_mind_energy():
    """Get mind energy for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        energy = mind_energy_system.get_energy(user_id)
        return jsonify(energy), 200
    except Exception as e:
        print(f"[MindEnergy] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'generator_energy': 100,
            'max_energy': 100
        }), 500

@mind_energy_bp.route('/api/mind-energy/boost', methods=['POST'])
@mind_energy_bp.route('/vidgenerator/api/mind-energy/boost', methods=['POST'])
@rate_limit()
def boost_energy():
    """Boost energy (purchasable)"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        amount = int(data.get('amount', 20))
        
        result = mind_energy_system.boost_energy(user_id, amount)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mind_energy_bp.route('/api/mind-energy/upgrade', methods=['POST'])
@mind_energy_bp.route('/vidgenerator/api/mind-energy/upgrade', methods=['POST'])
@rate_limit()
def upgrade_max_energy():
    """Upgrade max energy capacity"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        new_max = int(data.get('new_max', 150))
        
        result = mind_energy_system.upgrade_max_energy(user_id, new_max)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mind_energy_bp.route('/api/mind-energy/upgrade-generator', methods=['POST'])
@mind_energy_bp.route('/vidgenerator/api/mind-energy/upgrade-generator', methods=['POST'])
@rate_limit()
def upgrade_generator():
    """Upgrade a specific generator"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        generator_type = data.get('generator_type', 'basic')
        
        result = mind_energy_system.upgrade_generator(user_id, generator_type)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mind_energy_bp.route('/api/mind-energy/unlock-generator', methods=['POST'])
@mind_energy_bp.route('/vidgenerator/api/mind-energy/unlock-generator', methods=['POST'])
@rate_limit()
def unlock_generator():
    """Unlock a new generator type"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        generator_type = data.get('generator_type', 'advanced')
        
        result = mind_energy_system.unlock_generator(user_id, generator_type)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@mind_energy_bp.route('/api/mind-energy/set-active', methods=['POST'])
@mind_energy_bp.route('/vidgenerator/api/mind-energy/set-active', methods=['POST'])
@rate_limit()
def set_active_generator():
    """Set the active generator"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        generator_type = data.get('generator_type', 'basic')
        
        result = mind_energy_system.set_active_generator(user_id, generator_type)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
