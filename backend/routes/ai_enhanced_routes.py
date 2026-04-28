"""
AI-Enhanced Routes
API endpoints for AI-enhanced features across all systems
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List
from datetime import datetime

ai_enhanced_bp = Blueprint('ai_enhanced', __name__)


@ai_enhanced_bp.route('/api/ai/browser-profiles/<profile_id>/analyze', methods=['GET'])
def analyze_browser_profile(profile_id):
    """Analyze browser profile with AI"""
    try:
        from backend.services.ai_enhanced_browser_profiles import ai_enhanced_browser_profiles
        
        analysis = ai_enhanced_browser_profiles.analyze_profile_behavior(profile_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/browser-profiles/<profile_id>/predict', methods=['GET'])
def predict_profile_actions(profile_id):
    """Predict profile actions with AI"""
    try:
        from backend.services.ai_enhanced_browser_profiles import ai_enhanced_browser_profiles
        
        prediction = ai_enhanced_browser_profiles.predict_profile_actions(profile_id)
        
        return jsonify({
            'success': True,
            'prediction': prediction
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/debugging/sessions/<session_id>/analyze', methods=['GET'])
def analyze_debug_session(session_id):
    """Analyze debug session with AI"""
    try:
        from backend.services.ai_enhanced_debugging import ai_enhanced_debugging
        
        analysis = ai_enhanced_debugging.analyze_session(session_id)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/debugging/sessions/<session_id>/predict-error', methods=['POST'])
def predict_error_likelihood(session_id):
    """Predict error likelihood with AI"""
    try:
        data = request.get_json() or {}
        action_type = data.get('action_type', 'unknown')
        
        from backend.services.ai_enhanced_debugging import ai_enhanced_debugging
        
        prediction = ai_enhanced_debugging.predict_error_likelihood(session_id, action_type)
        
        return jsonify({
            'success': True,
            'prediction': prediction
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/debugging/sessions/<session_id>/optimize', methods=['GET'])
def suggest_optimizations(session_id):
    """Suggest optimizations with AI"""
    try:
        from backend.services.ai_enhanced_debugging import ai_enhanced_debugging
        
        optimizations = ai_enhanced_debugging.suggest_optimizations(session_id)
        
        return jsonify({
            'success': True,
            'optimizations': optimizations
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/signals/process', methods=['POST'])
def process_signal_with_ai():
    """Process signal with AI"""
    try:
        data = request.get_json() or {}
        signal = data.get('signal')
        
        if not signal:
            return jsonify({
                'success': False,
                'error': 'signal is required'
            }), 400
        
        from backend.services.ai_enhanced_signals import ai_enhanced_signals
        
        result = ai_enhanced_signals.intelligent_signal_processing(signal)
        
        return jsonify({
            'success': True,
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/signals/predict-trends', methods=['GET'])
def predict_signal_trends():
    """Predict signal trends with AI"""
    try:
        category = request.args.get('category', 'general')
        limit = int(request.args.get('limit', 100))
        
        from backend.services.ai_enhanced_signals import ai_enhanced_signals
        
        prediction = ai_enhanced_signals.predict_signal_trends(category, limit)
        
        return jsonify({
            'success': True,
            'prediction': prediction
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/paths/correct-intelligent', methods=['POST'])
def intelligent_path_correction():
    """Intelligently correct path with AI"""
    try:
        data = request.get_json() or {}
        path = data.get('path')
        context = data.get('context', {})
        
        if not path:
            return jsonify({
                'success': False,
                'error': 'path is required'
            }), 400
        
        from backend.services.ai_enhanced_paths import ai_enhanced_paths
        
        corrected_path, correction_info = ai_enhanced_paths.intelligent_path_correction(path, context)
        
        return jsonify({
            'success': True,
            'original': path,
            'corrected': corrected_path,
            'correction_info': correction_info
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/paths/predict', methods=['POST'])
def predict_path_corrections():
    """Predict path corrections with AI"""
    try:
        data = request.get_json() or {}
        paths = data.get('paths', [])
        
        if not paths or not isinstance(paths, list):
            return jsonify({
                'success': False,
                'error': 'paths array is required'
            }), 400
        
        from backend.services.ai_enhanced_paths import ai_enhanced_paths
        
        predictions = ai_enhanced_paths.predict_path_corrections(paths)
        
        return jsonify({
            'success': True,
            'predictions': predictions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/intelligence/summary', methods=['GET'])
def get_ai_intelligence_summary():
    """Get AI intelligence summary across all systems"""
    try:
        from backend.services.agent_ai_intelligence import agent_ai_intelligence
        
        all_intelligence = agent_ai_intelligence.get_all_intelligence()
        
        return jsonify({
            'success': True,
            'intelligence': all_intelligence,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/agent-tasks/predict', methods=['POST'])
def predict_task_success():
    """Predict task success with AI"""
    try:
        data = request.get_json() or {}
        task_data = data.get('task_data', {})
        
        if not task_data:
            return jsonify({
                'success': False,
                'error': 'task_data is required'
            }), 400
        
        from backend.services.ai_enhanced_agent_tasks import ai_enhanced_agent_tasks
        
        prediction = ai_enhanced_agent_tasks.predict_task_success(task_data)
        
        return jsonify({
            'success': True,
            'prediction': prediction
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_enhanced_bp.route('/api/ai/insights', methods=['GET'])
def get_ai_insights():
    """Get AI-powered insights across all systems"""
    try:
        insights = {
            'browser_profiles': {},
            'debugging': {},
            'signals': {},
            'paths': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Get browser profile insights
        try:
            from backend.services.browser_profile_tracker import browser_profile_tracker
            profile_stats = browser_profile_tracker.get_profile_stats()
            insights['browser_profiles'] = {
                'total_profiles': profile_stats.get('total_profiles', 0),
                'active_profiles': profile_stats.get('active_profiles', 0)
            }
        except:
            pass
        
        # Get debugging insights
        try:
            from backend.services.debugging_database import debugging_database
            debug_stats = debugging_database.get_debugging_stats()
            insights['debugging'] = {
                'total_sessions': debug_stats.get('total_sessions', 0),
                'active_sessions': debug_stats.get('active_sessions', 0),
                'total_errors': debug_stats.get('total_errors', 0)
            }
        except:
            pass
        
        # Get signal insights
        try:
            from backend.services.signal_collector import signal_collector
            insights['signals'] = {
                'total_signals': len(signal_collector.signals.get('signals', [])),
                'paired_signals': len(signal_collector.paired_signals)
            }
        except:
            pass
        
        # Get path correction insights
        try:
            from backend.services.path_corrector import path_corrector
            path_stats = path_corrector.get_correction_statistics()
            insights['paths'] = {
                'total_corrections': path_stats.get('total_corrections', 0),
                'success_rate': path_stats.get('success_rate', 0)
            }
        except:
            pass
        
        return jsonify({
            'success': True,
            'insights': insights
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
