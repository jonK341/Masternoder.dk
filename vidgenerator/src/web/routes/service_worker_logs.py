"""
Service Worker Logs API
Returns logs from service worker for debugging and monitoring
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import json

service_worker_logs_bp = Blueprint('service_worker_logs', __name__)

# In-memory log storage (in production, use Redis or database)
_log_storage = {}


@service_worker_logs_bp.route('/api/service-worker/logs', methods=['GET'])
@service_worker_logs_bp.route('/vidgenerator/api/service-worker/logs', methods=['GET'])
def get_service_worker_logs():
    """Get service worker logs"""
    try:
        generation_id = request.args.get('generation_id')
        limit = int(request.args.get('limit', 100))
        
        if generation_id:
            logs = _log_storage.get(generation_id, [])
            return jsonify({
                'success': True,
                'generation_id': generation_id,
                'logs': logs[-limit:],  # Return last N logs
                'total': len(logs)
            })
        else:
            # Return all logs from all generations
            all_logs = []
            for gen_id, logs in _log_storage.items():
                all_logs.extend([{**log, 'generation_id': gen_id} for log in logs])
            
            # Sort by timestamp
            all_logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            
            return jsonify({
                'success': True,
                'logs': all_logs[:limit],
                'total': len(all_logs),
                'generations': list(_log_storage.keys())
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_worker_logs_bp.route('/api/service-worker/logs', methods=['POST'])
@service_worker_logs_bp.route('/vidgenerator/api/service-worker/logs', methods=['POST'])
def store_service_worker_log():
    """Store a log entry from service worker"""
    try:
        data = request.get_json() or {}
        
        generation_id = data.get('generation_id', 'default')
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': data.get('level', 'info'),
            'message': data.get('message', ''),
            'metadata': data.get('metadata', {})
        }
        
        if generation_id not in _log_storage:
            _log_storage[generation_id] = []
        
        _log_storage[generation_id].append(log_entry)
        
        # Keep only last 1000 logs per generation
        if len(_log_storage[generation_id]) > 1000:
            _log_storage[generation_id] = _log_storage[generation_id][-1000:]
        
        return jsonify({
            'success': True,
            'stored': True
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_worker_logs_bp.route('/api/service-worker/logs/<generation_id>', methods=['DELETE'])
@service_worker_logs_bp.route('/vidgenerator/api/service-worker/logs/<generation_id>', methods=['DELETE'])
def clear_service_worker_logs(generation_id):
    """Clear logs for a specific generation"""
    try:
        if generation_id in _log_storage:
            del _log_storage[generation_id]
        
        return jsonify({
            'success': True,
            'cleared': True
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

