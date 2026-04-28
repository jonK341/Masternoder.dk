"""
Signal Collector Routes
API endpoints for signal collection and processing
"""
from flask import Blueprint, request, jsonify
from typing import Dict

signal_collector_bp = Blueprint('signal_collector', __name__)


@signal_collector_bp.route('/api/signals/collect', methods=['POST'])
def collect_signal():
    """Collect a signal"""
    try:
        data = request.get_json() or {}
        source = data.get('source', 'unknown')
        signal_type = data.get('signal_type', 'general')
        signal_data = data.get('data', {})
        metadata = data.get('metadata')
        
        from backend.services.signal_collector import signal_collector
        
        signal = signal_collector.collect_signal(
            source=source,
            signal_type=signal_type,
            data=signal_data,
            metadata=metadata
        )
        
        return jsonify({
            'success': True,
            'signal': signal
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@signal_collector_bp.route('/api/signals/invoke', methods=['POST'])
def process_invoke():
    """Process INVOKE messages"""
    try:
        data = request.get_json() or {}
        message = data.get('message', '')
        
        if not message:
            return jsonify({
                'success': False,
                'error': 'message is required'
            }), 400
        
        from backend.services.signal_collector import signal_collector
        
        signal = signal_collector.process_invoke_message(message)
        
        return jsonify({
            'success': True,
            'signal': signal,
            'message': 'Signal collected and fed to brain'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@signal_collector_bp.route('/api/signals/list', methods=['GET'])
def list_signals():
    """List collected signals"""
    try:
        source = request.args.get('source')
        category = request.args.get('category')
        limit = int(request.args.get('limit', 100))
        
        from backend.services.signal_collector import signal_collector
        
        signals = signal_collector.get_signals(
            source=source,
            category=category,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'signals': signals,
            'count': len(signals)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@signal_collector_bp.route('/api/signals/paired', methods=['GET'])
def get_paired_signals():
    """Get paired signals"""
    try:
        limit = int(request.args.get('limit', 50))
        
        from backend.services.signal_collector import signal_collector
        
        paired = signal_collector.get_paired_signals(limit=limit)
        
        return jsonify({
            'success': True,
            'paired_signals': paired,
            'count': len(paired)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@signal_collector_bp.route('/api/signals/stats', methods=['GET'])
def get_signal_stats():
    """Get signal collection statistics"""
    try:
        from backend.services.signal_collector import signal_collector
        
        stats = {
            'total_signals': len(signal_collector.signals.get('signals', [])),
            'sources': signal_collector.signals.get('sources', {}),
            'categories': signal_collector.signals.get('categories', {}),
            'paired_signals': len(signal_collector.paired_signals)
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
