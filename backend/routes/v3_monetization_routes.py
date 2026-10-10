"""
V3 Monetization Integration Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.v3_monetization_integration import v3_monetization_integration
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

v3_monetization_bp = Blueprint('v3_monetization', __name__)


@v3_monetization_bp.route('/api/v3-monetization/shop-purchase', methods=['POST'])
@rate_limit
def integrate_shop_purchase():
    """Integrate shop v3 purchase with monetization"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        item_id = InputValidator.sanitize_string(data.get('item_id', ''))
        purchase_data = data.get('purchase_data', {})
        
        if not item_id:
            return jsonify({'success': False, 'error': 'item_id required'}), 400
        
        result = v3_monetization_integration.integrate_shop_v3_purchase(user_id, item_id, purchase_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@v3_monetization_bp.route('/api/v3-monetization/battle-purchase', methods=['POST'])
@rate_limit
def integrate_battle_purchase():
    """Integrate battle v3 with monetization"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        battle_type = InputValidator.sanitize_string(data.get('battle_type', ''))
        purchase_data = data.get('purchase_data', {})
        
        if not battle_type:
            return jsonify({'success': False, 'error': 'battle_type required'}), 400
        
        result = v3_monetization_integration.integrate_battle_v3_purchase(user_id, battle_type, purchase_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@v3_monetization_bp.route('/api/v3-monetization/vidgenerator-purchase', methods=['POST'])
@rate_limit
def integrate_vidgenerator_purchase():
    """Integrate vidgenerator v3 with monetization"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        quality_preset = InputValidator.sanitize_string(data.get('quality_preset', ''))
        purchase_data = data.get('purchase_data', {})
        
        if not quality_preset:
            return jsonify({'success': False, 'error': 'quality_preset required'}), 400
        
        result = v3_monetization_integration.integrate_vidgenerator_v3_purchase(user_id, quality_preset, purchase_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@v3_monetization_bp.route('/api/v3-monetization/stats', methods=['GET'])
def get_v3_monetization_stats():
    """Get V3 monetization stats"""
    try:
        result = v3_monetization_integration.get_v3_monetization_stats()
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@v3_monetization_bp.route('/api/v3-monetization/unlocks/<user_id>', methods=['GET'])
def get_user_v3_unlocks(user_id):
    """Get user's V3 unlocks"""
    try:
        result = v3_monetization_integration.get_user_v3_unlocks(user_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

