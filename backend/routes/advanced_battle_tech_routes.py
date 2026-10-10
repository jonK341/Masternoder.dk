"""
Advanced Battle Tech Routes
Dedicated routes for advanced battle technology system
"""
from flask import Blueprint, request, jsonify
import uuid
from backend.services.advanced_battle_tech import advanced_battle_tech
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

advanced_battle_tech_bp = Blueprint('advanced_battle_tech', __name__)


@advanced_battle_tech_bp.route('/api/battle/advanced-tech/available', methods=['GET'])
@advanced_battle_tech_bp.route('/vidgenerator/api/battle/advanced-tech/available', methods=['GET'])
@rate_limit()
def get_advanced_tech_available():
    """Get available advanced battle tech"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            # Try both method names for compatibility
            if hasattr(advanced_battle_tech, 'get_available_tech'):
                available = advanced_battle_tech.get_available_tech(user_id)
            elif hasattr(advanced_battle_tech, 'get_available_advanced_tech'):
                available = advanced_battle_tech.get_available_advanced_tech()
            else:
                available = {'success': True, 'tech': {}}
            return jsonify(available), 200
        except ImportError:
            return jsonify({
                'success': True,
                'tech': {},
                'message': 'Advanced tech system not available'
            }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@advanced_battle_tech_bp.route('/api/battle/advanced-tech/unlock', methods=['POST'])
@advanced_battle_tech_bp.route('/vidgenerator/api/battle/advanced-tech/unlock', methods=['POST'])
@rate_limit()
def unlock_advanced_tech():
    """Unlock advanced battle technology"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        tech_name = InputValidator.sanitize_string(data.get('tech_name', ''))
        requirements_met = data.get('requirements_met', [])
        
        if not tech_name:
            return jsonify({'success': False, 'error': 'tech_name required'}), 400
        
        try:
            result = advanced_battle_tech.unlock_advanced_tech(user_id, tech_name, requirements_met)
            return jsonify(result), 200
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Advanced tech system not available'
            }), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@advanced_battle_tech_bp.route('/api/battle/advanced-tech/combine', methods=['POST'])
@advanced_battle_tech_bp.route('/vidgenerator/api/battle/advanced-tech/combine', methods=['POST'])
@rate_limit()
def combine_tech():
    """Combine multiple advanced tech for battle"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        tech_ids = data.get('tech_ids', [])
        combination_name = data.get('combination_name', 'Ultimate Battle Tech')
        
        if not tech_ids or len(tech_ids) < 2:
            return jsonify({'success': False, 'error': 'Need at least 2 tech_ids'}), 400
        
        try:
            result = advanced_battle_tech.combine_tech_for_battle(user_id, tech_ids, combination_name)
            return jsonify(result), 200
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Advanced tech system not available'
            }), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@advanced_battle_tech_bp.route('/api/battle/advanced-tech/list', methods=['GET'])
@advanced_battle_tech_bp.route('/vidgenerator/api/battle/advanced-tech/list', methods=['GET'])
@rate_limit()
def list_advanced_tech():
    """List all advanced tech with user unlock status"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            result = advanced_battle_tech.get_all_tech_with_status(user_id)
            return jsonify(result), 200
        except ImportError:
            return jsonify({
                'success': True,
                'tech': [],
                'message': 'Advanced tech system not available'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_battle_tech_bp.route('/api/battle/advanced-tech/<tech_name>/status', methods=['GET'])
@advanced_battle_tech_bp.route('/vidgenerator/api/battle/advanced-tech/<tech_name>/status', methods=['GET'])
@rate_limit()
def get_tech_status(tech_name):
    """Get status of specific advanced tech"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            result = advanced_battle_tech.get_tech_status(user_id, tech_name)
            return jsonify(result), 200
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Advanced tech system not available'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@advanced_battle_tech_bp.route('/api/battle/impressiveness/<user_id>', methods=['GET'])
@advanced_battle_tech_bp.route('/vidgenerator/api/battle/impressiveness/<user_id>', methods=['GET'])
@rate_limit()
def get_user_impressiveness(user_id):
    """Get user impressiveness score"""
    try:
        try:
            result = advanced_battle_tech.get_user_impressiveness(user_id)
            return jsonify(result), 200
        except ImportError:
            return jsonify({
                'success': True,
                'impressiveness_score': 0,
                'message': 'Advanced tech system not available'
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
