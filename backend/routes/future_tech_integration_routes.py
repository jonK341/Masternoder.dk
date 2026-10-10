"""
Future Tech Integration Routes
API routes for future tech integration service
"""
from flask import Blueprint, request, jsonify
from backend.services.future_tech_integration_service import future_tech_integration_service
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

future_tech_integration_bp = Blueprint('future_tech_integration', __name__)

@future_tech_integration_bp.route('/api/future-tech/status', methods=['GET'])
@future_tech_integration_bp.route('/vidgenerator/api/future-tech/status', methods=['GET'])
@rate_limit()
def get_integration_status():
    """Get integration status of all future tech and calculator systems"""
    try:
        result = future_tech_integration_service.get_integration_status()
        return jsonify({
            'success': True,
            'status': result
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_integration_bp.route('/api/future-tech/solve-equation', methods=['POST'])
@future_tech_integration_bp.route('/vidgenerator/api/future-tech/solve-equation', methods=['POST'])
@rate_limit()
def solve_equation():
    """Solve equation using advanced intelligent calculator"""
    try:
        data = InputValidator.get_json_safe(default={})
        equation = data.get('equation', '')
        context = data.get('context', {})
        
        if not equation and not context.get('point_data'):
            return jsonify({
                'success': False,
                'error': 'equation or context.point_data required'
            }), 400
        
        result = future_tech_integration_service.solve_equation(equation, context)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

