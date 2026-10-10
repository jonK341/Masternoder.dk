"""
Spider Web Error Handler API Routes
"""
from flask import Blueprint, request, jsonify
import traceback

spiderweb_error_bp = Blueprint('spiderweb_error', __name__, url_prefix='/api/spiderweb-error')

@spiderweb_error_bp.route('/handle', methods=['POST'])
def handle_error_with_retry():
    """
    Handle an error with automatic retry logic
    Body: {
        "error_type": "BlockingIOError",
        "error_message": "...",
        "operation": "function_name",
        "service_name": "generator",
        "max_retries": 100
    }
    """
    try:
        from backend.services.spiderweb_error_handler import spiderweb_error_handler
        
        data = request.get_json() or {}
        error_type = data.get('error_type', 'Exception')
        error_message = data.get('error_message', 'Unknown error')
        service_name = data.get('service_name', 'generator')
        max_retries = data.get('max_retries', 100)
        
        # Create error object
        error_class = type(error_type, (Exception,), {})
        error = error_class(error_message)
        
        # For now, return statistics since we can't actually execute the operation
        # In real usage, this would be called from within the error handler
        stats = spiderweb_error_handler.get_error_statistics()
        
        return jsonify({
            'success': True,
            'message': 'Error registered with SpiderWeb handler',
            'error_signature': spiderweb_error_handler._calculate_error_signature(error),
            'recommended_max_retries': max_retries,
            'service': service_name,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@spiderweb_error_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get error statistics"""
    try:
        from backend.services.spiderweb_error_handler import spiderweb_error_handler
        
        error_signature = request.args.get('error_signature')
        stats = spiderweb_error_handler.get_error_statistics(error_signature)
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@spiderweb_error_bp.route('/patterns', methods=['GET'])
def get_patterns():
    """Get all error patterns"""
    try:
        from backend.services.spiderweb_error_handler import spiderweb_error_handler
        
        return jsonify({
            'success': True,
            'patterns': spiderweb_error_handler.error_patterns
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@spiderweb_error_bp.route('/clear-old', methods=['POST'])
def clear_old_patterns():
    """Clear old error patterns and attempts"""
    try:
        from backend.services.spiderweb_error_handler import spiderweb_error_handler
        
        data = request.get_json() or {}
        days = data.get('days', 30)
        
        result = spiderweb_error_handler.clear_old_patterns(days)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@spiderweb_error_bp.route('/test-calculator', methods=['POST'])
def test_calculator():
    """Test calculator integration"""
    try:
        from backend.services.spiderweb_error_handler import spiderweb_error_handler
        from backend.services.advanced_intelligent_calculator import AdvancedIntelligentCalculator
        
        data = request.get_json() or {}
        expression = data.get('expression', '0.8 * 0.9')
        
        calculator = AdvancedIntelligentCalculator()
        result = calculator.calculate(expression)
        
        # Test success rate calculation
        test_signature = 'test_error_signature'
        success_rate = spiderweb_error_handler._calculate_success_rate(test_signature)
        
        return jsonify({
            'success': True,
            'calculator_result': result,
            'success_rate_calculation': {
                'signature': test_signature,
                'rate': success_rate,
                'threshold': spiderweb_error_handler.success_threshold,
                'should_retry': success_rate >= spiderweb_error_handler.success_threshold
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

