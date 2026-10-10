"""
Shop v3 Ultimate Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.shop_v3_ultimate import shop_v3_ultimate
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

shop_v3_bp = Blueprint('shop_v3', __name__)

def get_user_id():
    """Get user ID from session or request"""
    from flask import session
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session.get('user_id', request.args.get('user_id', 'anonymous'))


@shop_v3_bp.route('/api/shop-v3/items')
@shop_v3_bp.route('/vidgenerator/api/shop-v3/items')
@rate_limit()
def get_all_items():
    """Get all shop items"""
    try:
        result = shop_v3_ultimate.get_all_items()
        return jsonify({
            'success': True,
            **result
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@shop_v3_bp.route('/api/shop-v3/recommendations')
@shop_v3_bp.route('/vidgenerator/api/shop-v3/recommendations')
@rate_limit()
def get_recommendations():
    """Get intelligent recommendations"""
    try:
        user_id = get_user_id()
        result = shop_v3_ultimate.get_intelligent_recommendations(user_id)
        return jsonify({
            'success': True,
            **result
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@shop_v3_bp.route('/api/shop-v3/purchase', methods=['POST'])
@shop_v3_bp.route('/vidgenerator/api/shop-v3/purchase', methods=['POST'])
@rate_limit()
def purchase_item():
    """Purchase item"""
    try:
        user_id = get_user_id()
        data = request.get_json() or {}
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))
        
        result = shop_v3_ultimate.purchase_item(user_id, item_id, quantity)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

