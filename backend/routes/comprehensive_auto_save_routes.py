"""
Comprehensive Auto-Save Routes
Auto-save all user data, progress, points, energy
"""
from flask import Blueprint, jsonify, request
from backend.services.comprehensive_auto_save import comprehensive_auto_save
from backend.services.unified_point_system_json_storage import unified_point_json_storage
from backend.services.ultra_resource_controller import ultra_resource_controller
from backend.services.unified_game_mechanics_constructor import unified_game_mechanics
from datetime import datetime

comprehensive_auto_save_bp = Blueprint('comprehensive_auto_save', __name__)


@comprehensive_auto_save_bp.route('/api/auto-save/points', methods=['POST'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/points', methods=['POST'])
def auto_save_points():
    """Auto-save points"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        # Get current points
        points = unified_point_json_storage.get_all_points(user_id)
        
        # Auto-save
        result = comprehensive_auto_save.auto_save_points(user_id, points)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comprehensive_auto_save_bp.route('/api/auto-save/energy', methods=['POST'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/energy', methods=['POST'])
def auto_save_energy():
    """Auto-save energy"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        # Get current energy
        energy = ultra_resource_controller.get_energy_status(user_id)
        
        # Auto-save
        result = comprehensive_auto_save.auto_save_energy(user_id, energy)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comprehensive_auto_save_bp.route('/api/auto-save/progress', methods=['POST'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/progress', methods=['POST'])
def auto_save_progress():
    """Auto-save progress"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        # Get current progress
        progress = unified_game_mechanics.get_user_progress(user_id)
        
        # Auto-save
        result = comprehensive_auto_save.auto_save_progress(user_id, progress)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comprehensive_auto_save_bp.route('/api/auto-save/full', methods=['POST'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/full', methods=['POST'])
def auto_save_full():
    """Auto-save complete user data snapshot"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        # Get all data
        all_data = {
            'points': unified_point_json_storage.get_all_points(user_id),
            'energy': ultra_resource_controller.get_energy_status(user_id),
            'progress': unified_game_mechanics.get_user_progress(user_id),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Auto-save
        result = comprehensive_auto_save.auto_save_full(user_id, all_data)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comprehensive_auto_save_bp.route('/api/auto-save/state', methods=['POST'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/state', methods=['POST'])
def auto_save_state():
    """Auto-save state"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        state_data = data.get('state', {})
        
        result = comprehensive_auto_save.auto_save_state(user_id, state_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comprehensive_auto_save_bp.route('/api/auto-save/status', methods=['GET'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/status', methods=['GET'])
def get_auto_save_status():
    """Get auto-save status"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = comprehensive_auto_save.get_save_status(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@comprehensive_auto_save_bp.route('/api/auto-save/load', methods=['GET'])
@comprehensive_auto_save_bp.route('/vidgenerator/api/auto-save/load', methods=['GET'])
def load_auto_save():
    """Load auto-saved data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        save_type = request.args.get('save_type', 'full')
        
        result = comprehensive_auto_save.load_auto_save(user_id, save_type)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

