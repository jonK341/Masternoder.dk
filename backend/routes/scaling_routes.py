"""
Scaling Routes - API routes for scaling system (1.3 billion users)
"""
from flask import Blueprint, request, jsonify
from backend.services.scaling_event_system import scaling_event_system
from backend.services.scaling_calculator_distributed import scaling_calculator_distributed
from backend.services.scaling_cache_system import user_cache, calculation_cache, stats_cache
from backend.services.scaling_queue_system import calculation_queue, event_queue
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

scaling_bp = Blueprint('scaling', __name__)

# ==================== EVENT SYSTEM ROUTES ====================

@scaling_bp.route('/api/scaling/events/emit', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/events/emit', methods=['POST'])
@rate_limit()
def emit_event():
    """Emit an event"""
    try:
        data = InputValidator.get_json_safe(default={})
        event_type = InputValidator.sanitize_string(data.get('event_type', ''))
        event_data = data.get('event_data', {})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        priority = int(data.get('priority', 5))
        
        if not event_type:
            return jsonify({
                'success': False,
                'error': 'event_type required'
            }), 400
        
        result = scaling_event_system.emit(event_type, event_data, user_id, priority)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/events/register-handler', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/events/register-handler', methods=['POST'])
@rate_limit()
def register_handler():
    """Register an event handler (programmatic, requires handler function)"""
    return jsonify({
        'success': False,
        'error': 'Handlers must be registered programmatically. Use scaling_event_system.register_handler()'
    }), 400


@scaling_bp.route('/api/scaling/events/stats', methods=['GET'])
@scaling_bp.route('/vidgenerator/api/scaling/events/stats', methods=['GET'])
@rate_limit()
def get_event_stats():
    """Get event system statistics"""
    try:
        stats = scaling_event_system.get_stats()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/events/start-workers', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/events/start-workers', methods=['POST'])
@rate_limit()
def start_workers():
    """Start event processing workers"""
    try:
        num_workers = int(request.args.get('workers', 10))
        result = scaling_event_system.start_workers(num_workers)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/events/stop-workers', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/events/stop-workers', methods=['POST'])
@rate_limit()
def stop_workers():
    """Stop event processing workers"""
    try:
        result = scaling_event_system.stop_workers()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# ==================== CALCULATOR ROUTES ====================

@scaling_bp.route('/api/scaling/calculator/calculate-async', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/calculator/calculate-async', methods=['POST'])
@rate_limit()
def calculate_async():
    """Calculate asynchronously (queued)"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        point_data = data.get('point_data', {})
        priority = InputValidator.sanitize_string(data.get('priority', 'medium'))
        use_cache = bool(data.get('use_cache', True))
        
        if not user_id or not point_data:
            return jsonify({
                'success': False,
                'error': 'user_id and point_data required'
            }), 400
        
        result = scaling_calculator_distributed.calculate_async(
            user_id, point_data, priority, use_cache
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/calculator/calculate-sync', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/calculator/calculate-sync', methods=['POST'])
@rate_limit()
def calculate_sync():
    """Calculate synchronously (immediate)"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        point_data = data.get('point_data', {})
        use_cache = bool(data.get('use_cache', True))
        
        if not user_id or not point_data:
            return jsonify({
                'success': False,
                'error': 'user_id and point_data required'
            }), 400
        
        result = scaling_calculator_distributed.calculate_sync(user_id, point_data, use_cache)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/calculator/result/<calculation_id>', methods=['GET'])
@scaling_bp.route('/vidgenerator/api/scaling/calculator/result/<calculation_id>', methods=['GET'])
@rate_limit()
def get_calculation_result(calculation_id: str):
    """Get calculation result"""
    try:
        result = scaling_calculator_distributed.get_calculation_result(calculation_id)
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/calculator/stats', methods=['GET'])
@scaling_bp.route('/vidgenerator/api/scaling/calculator/stats', methods=['GET'])
@rate_limit()
def get_calculator_stats():
    """Get calculator statistics"""
    try:
        stats = scaling_calculator_distributed.get_stats()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# ==================== CACHE ROUTES ====================

@scaling_bp.route('/api/scaling/cache/stats', methods=['GET'])
@scaling_bp.route('/vidgenerator/api/scaling/cache/stats', methods=['GET'])
@rate_limit()
def get_cache_stats():
    """Get cache statistics"""
    try:
        stats = {
            'user_cache': user_cache.get_stats() if user_cache else {},
            'calculation_cache': calculation_cache.get_stats() if calculation_cache else {},
            'stats_cache': stats_cache.get_stats() if stats_cache else {}
        }
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# ==================== QUEUE ROUTES ====================

@scaling_bp.route('/api/scaling/queues/stats', methods=['GET'])
@scaling_bp.route('/vidgenerator/api/scaling/queues/stats', methods=['GET'])
@rate_limit()
def get_queue_stats():
    """Get queue statistics"""
    try:
        stats = {
            'calculation_queue': calculation_queue.get_stats() if calculation_queue else {},
            'event_queue': event_queue.get_stats() if event_queue else {}
        }
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/workers/start', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/workers/start', methods=['POST'])
@rate_limit()
def start_workers():
    """Start background workers"""
    try:
        from backend.services.scaling_worker_service import scaling_worker_service
        calculation_workers = int(request.args.get('calculation_workers', 20))
        event_workers = int(request.args.get('event_workers', 10))
        
        result = scaling_worker_service.start_workers(calculation_workers, event_workers)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@scaling_bp.route('/api/scaling/workers/stop', methods=['POST'])
@scaling_bp.route('/vidgenerator/api/scaling/workers/stop', methods=['POST'])
@rate_limit()
def stop_workers():
    """Stop background workers"""
    try:
        from backend.services.scaling_worker_service import scaling_worker_service
        result = scaling_worker_service.stop_workers()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

