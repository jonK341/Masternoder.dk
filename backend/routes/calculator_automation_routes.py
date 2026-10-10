"""
Calculator Automation Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.calculator_automation import calculator_automation
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

calculator_automation_bp = Blueprint('calculator_automation', __name__)


@calculator_automation_bp.route('/api/calculator-automation/start', methods=['POST'])
@calculator_automation_bp.route('/vidgenerator/api/calculator-automation/start', methods=['POST'])
@rate_limit()
def start_automation():
    """Start calculator automation"""
    try:
        result = calculator_automation.start()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@calculator_automation_bp.route('/api/calculator-automation/stop', methods=['POST'])
@calculator_automation_bp.route('/vidgenerator/api/calculator-automation/stop', methods=['POST'])
@rate_limit()
def stop_automation():
    """Stop calculator automation"""
    try:
        result = calculator_automation.stop()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@calculator_automation_bp.route('/api/calculator-automation/status')
@calculator_automation_bp.route('/vidgenerator/api/calculator-automation/status')
@rate_limit()
def get_status():
    """Get automation status"""
    try:
        status = calculator_automation.get_status()
        return jsonify({
            'success': True,
            'status': status
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@calculator_automation_bp.route('/api/calculator-automation/calculate-now', methods=['POST'])
@calculator_automation_bp.route('/vidgenerator/api/calculator-automation/calculate-now', methods=['POST'])
@rate_limit()
def calculate_now():
    """Trigger immediate calculation"""
    try:
        user_id = request.json.get('user_id') if request.json else None
        result = calculator_automation.calculate_now(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

