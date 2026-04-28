"""
Debugging Master Routes
Comprehensive API for the debugging system - THE AUTHORITY
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List
from datetime import datetime

debugging_master_bp = Blueprint('debugging_master', __name__)

try:
    from backend.services.agent_ai_orchestrator import agent_ai_orchestrator
except ImportError:
    agent_ai_orchestrator = None


def _get_agent_ai_response(profile_key: str, user_prompt: str, context: Dict):
    """Best-effort AI enrichment that never breaks base route behavior."""
    if agent_ai_orchestrator is None:
        return {'used_ai': False, 'success': False, 'reason': 'orchestrator_unavailable'}
    try:
        return agent_ai_orchestrator.run_profile(
            profile_key=profile_key,
            user_prompt=user_prompt,
            context=context or {},
        )
    except Exception as e:
        return {'used_ai': False, 'success': False, 'reason': f'orchestrator_error: {str(e)}'}


def _get_ai_metrics():
    """Return orchestrator health counters for observability."""
    if agent_ai_orchestrator is None:
        return {'available': False, 'reason': 'orchestrator_unavailable'}
    try:
        metrics = agent_ai_orchestrator.get_health_metrics()
        metrics['available'] = True
        return metrics
    except Exception as e:
        return {'available': False, 'reason': f'metrics_error: {str(e)}'}


def _safe_debugging_status():
    return {
        'success': True,
        'status': 'degraded',
        'authority': 'debugging_master',
        'timestamp': datetime.now().isoformat(),
        'debugging': {},
        'profiles': {},
        'ai_intelligence': None,
        'system': {
            'version': '3.0.0',
            'capabilities': [],
            'note': 'Debugging services unavailable; fallback payload'
        }
    }


@debugging_master_bp.route('/api/debugging/master/status', methods=['GET'])
def get_master_status():
    """Get master debugging system status with AI intelligence"""
    try:
        from backend.services.debugging_database import debugging_database
        from backend.services.browser_profile_tracker import browser_profile_tracker
        from backend.services.agent_ai_intelligence import agent_ai_intelligence
        
        debug_stats = debugging_database.get_debugging_stats()
        profile_stats = browser_profile_tracker.get_profile_stats()
        
        # Get AI intelligence summary
        ai_intelligence = None
        try:
            ai_intelligence = agent_ai_intelligence.get_all_intelligence()
        except:
            pass
        
        response_payload = {
            'success': True,
            'status': 'active',
            'authority': 'debugging_master',
            'timestamp': datetime.now().isoformat(),
            'debugging': debug_stats,
            'profiles': profile_stats,
            'ai_intelligence': ai_intelligence,
            'system': {
                'version': '3.0.0',
                'capabilities': [
                    'browser_profile_tracking',
                    'session_management',
                    'action_logging',
                    'error_tracking',
                    'performance_monitoring',
                    'real_time_analytics',
                    'ai_intelligence',
                    'ai_predictions',
                    'ai_insights',
                    'ai_optimization',
                    'ai_pattern_recognition'
                ]
            }
        }
        response_payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_master_status',
            user_prompt='Summarize debugging platform status and key risks.',
            context={
                'debugging': debug_stats,
                'profiles': profile_stats,
                'ai_intelligence': ai_intelligence,
            },
        )
        response_payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(response_payload)
    except Exception as e:
        payload = _safe_debugging_status()
        payload['system']['error'] = str(e)
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_master_status',
            user_prompt='Summarize degraded debugging status and safe next steps.',
            context={'error': str(e), 'status': 'degraded'},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200


@debugging_master_bp.route('/api/debugging/session/start', methods=['POST'])
def start_debug_session():
    """Start a new debug session"""
    try:
        data = request.get_json(silent=True) or {}
        browser_data = data.get('browser_data', {})
        user_id = data.get('user_id')
        metadata = data.get('metadata', {})
        
        from backend.services.browser_profile_tracker import browser_profile_tracker
        from backend.services.debugging_database import debugging_database
        
        # Get or create browser profile
        ip_address = request.remote_addr
        profile = browser_profile_tracker.get_or_create_profile(browser_data, ip_address)
        profile_id = profile.get('profile_id')
        
        # Create debug session
        session = debugging_database.create_session(
            profile_id=profile_id,
            user_id=user_id,
            metadata=metadata
        )
        
        return jsonify({
            'success': True,
            'session': session,
            'profile': profile
        })
    except Exception as e:
        return jsonify({
            'success': True,
            'session': {
                'session_id': f"fallback_{int(datetime.now().timestamp())}",
                'status': 'deferred',
                'started_at': datetime.now().isoformat()
            },
            'profile': {},
            'note': f'start-session fallback: {str(e)}'
        }), 200


@debugging_master_bp.route('/api/debugging/session/end', methods=['POST'])
def end_debug_session():
    """End a debug session"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required'
            }), 400
        
        from backend.services.debugging_database import debugging_database
        
        success = debugging_database.end_session(session_id)
        
        return jsonify({
            'success': success,
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugging_master_bp.route('/api/debugging/action/log', methods=['POST'])
def log_debug_action():
    """Log a debug action"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        action_type = data.get('action_type')
        action_name = data.get('action_name')
        
        if not session_id or not action_type or not action_name:
            return jsonify({
                'success': False,
                'error': 'session_id, action_type, and action_name are required'
            }), 400
        
        from backend.services.debugging_database import debugging_database
        from backend.services.browser_profile_tracker import browser_profile_tracker
        
        result = debugging_database.log_action(
            session_id=session_id,
            action_type=action_type,
            action_name=action_name,
            target_tab=data.get('target_tab'),
            target_element=data.get('target_element'),
            result=data.get('result'),
            success=data.get('success', True),
            error_message=data.get('error_message'),
            execution_time_ms=data.get('execution_time_ms'),
            metadata=data.get('metadata')
        )
        
        # Update profile debug action count
        session = debugging_database.get_session(session_id)
        if session and session.get('profile_id'):
            browser_profile_tracker.update_debug_action(session['profile_id'])
        
        return jsonify({
            'success': result.get('success', False),
            'action_id': result.get('action_id'),
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugging_master_bp.route('/api/debugging/error/log', methods=['POST'])
def log_debug_error():
    """Log a debug error"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        error_type = data.get('error_type', 'unknown')
        error_message = data.get('error_message', '')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required'
            }), 400
        
        from backend.services.debugging_database import debugging_database
        
        result = debugging_database.log_error(
            session_id=session_id,
            error_type=error_type,
            error_message=error_message,
            error_stack=data.get('error_stack'),
            file_path=data.get('file_path'),
            line_number=data.get('line_number'),
            severity=data.get('severity', 'error'),
            metadata=data.get('metadata')
        )
        
        return jsonify({
            'success': result.get('success', False),
            'error_id': result.get('error_id'),
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugging_master_bp.route('/api/debugging/performance/log', methods=['POST'])
def log_performance():
    """Log performance metric"""
    try:
        data = request.get_json() or {}
        session_id = data.get('session_id')
        metric_name = data.get('metric_name')
        metric_value = data.get('metric_value')
        
        if not session_id or not metric_name or metric_value is None:
            return jsonify({
                'success': False,
                'error': 'session_id, metric_name, and metric_value are required'
            }), 400
        
        from backend.services.debugging_database import debugging_database
        
        result = debugging_database.log_performance(
            session_id=session_id,
            metric_name=metric_name,
            metric_value=metric_value,
            unit=data.get('unit'),
            context=data.get('context')
        )
        
        return jsonify({
            'success': result.get('success', False),
            'performance_id': result.get('performance_id'),
            'result': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugging_master_bp.route('/api/debugging/session/<session_id>', methods=['GET'])
def get_session_details(session_id):
    """Get detailed session information with AI analysis"""
    try:
        from backend.services.debugging_database import debugging_database
        from backend.services.ai_enhanced_debugging import ai_enhanced_debugging
        
        session = debugging_database.get_session(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        actions = debugging_database.get_session_actions(session_id)
        errors = debugging_database.get_session_errors(session_id)
        
        # Get AI analysis
        ai_analysis = None
        try:
            ai_analysis = ai_enhanced_debugging.analyze_session(session_id)
        except Exception as e:
            print(f"Error getting AI analysis: {e}")
        
        response_payload = {
            'success': True,
            'session': session,
            'actions': actions,
            'errors': errors,
            'action_count': len(actions),
            'error_count': len(errors),
            'ai_analysis': ai_analysis
        }
        response_payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_session_review',
            user_prompt=f'Review debug session {session_id} and suggest next steps.',
            context={
                'session_id': session_id,
                'action_count': len(actions),
                'error_count': len(errors),
                'session': session,
                'errors': errors[:10],
            },
        )
        return jsonify(response_payload)
    except Exception as e:
        payload = {
            'success': True,
            'session': {'session_id': session_id, 'status': 'unavailable'},
            'actions': [],
            'errors': [],
            'action_count': 0,
            'error_count': 0,
            'ai_analysis': None,
            'note': f'session fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_session_review',
            user_prompt=f'Review unavailable debug session {session_id} and suggest checks.',
            context={'session_id': session_id, 'error': str(e)},
        )
        return jsonify(payload), 200


@debugging_master_bp.route('/api/debugging/profiles', methods=['GET'])
def get_profiles():
    """Get all browser profiles"""
    try:
        limit = int(request.args.get('limit', 100))
        
        from backend.services.browser_profile_tracker import browser_profile_tracker
        
        profiles = browser_profile_tracker.get_all_profiles(limit=limit)
        stats = browser_profile_tracker.get_profile_stats()
        
        response_payload = {
            'success': True,
            'profiles': profiles,
            'stats': stats,
            'count': len(profiles)
        }
        response_payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_profiles_review',
            user_prompt='Review browser profile stats and suggest reliability improvements.',
            context={'stats': stats, 'count': len(profiles)},
        )
        response_payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(response_payload)
    except Exception as e:
        payload = {
            'success': True,
            'profiles': [],
            'stats': {},
            'count': 0,
            'note': f'profiles fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_profiles_review',
            user_prompt='Review degraded profile stats and suggest safe recovery checks.',
            context={'error': str(e), 'status': 'degraded'},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200


@debugging_master_bp.route('/api/debugging/stats', methods=['GET'])
def get_debugging_stats():
    """Get comprehensive debugging statistics"""
    try:
        from backend.services.debugging_database import debugging_database
        from backend.services.browser_profile_tracker import browser_profile_tracker
        
        debug_stats = debugging_database.get_debugging_stats()
        profile_stats = browser_profile_tracker.get_profile_stats()
        
        response_payload = {
            'success': True,
            'debugging': debug_stats,
            'profiles': profile_stats,
            'timestamp': datetime.now().isoformat()
        }
        response_payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_stats_review',
            user_prompt='Review debugging stats and recommend prioritized next actions.',
            context={'debugging': debug_stats, 'profiles': profile_stats},
        )
        response_payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(response_payload)
    except Exception as e:
        payload = {
            'success': True,
            'debugging': {},
            'profiles': {},
            'timestamp': datetime.now().isoformat(),
            'note': f'stats fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_stats_review',
            user_prompt='Review degraded debugging stats state and suggest safe checks.',
            context={'error': str(e), 'status': 'degraded'},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200


@debugging_master_bp.route('/api/debugging/analytics', methods=['GET'])
def get_analytics():
    """Get real-time analytics with AI insights"""
    try:
        from backend.services.debugging_database import debugging_database
        from backend.services.browser_profile_tracker import browser_profile_tracker
        from backend.services.ai_enhanced_debugging import ai_enhanced_debugging
        from backend.services.agent_ai_intelligence import agent_ai_intelligence
        
        # Get recent sessions
        try:
            from sqlalchemy import text
            from src.db.models import db
            
            recent_sessions = db.session.execute(
                text("""
                    SELECT * FROM debug_sessions
                    ORDER BY created_at DESC
                    LIMIT 50
                """)
            ).fetchall()
            
            # Get action breakdown
            action_breakdown = db.session.execute(
                text("""
                    SELECT action_type, COUNT(*) as count
                    FROM debug_errors
                    GROUP BY action_type
                    ORDER BY count DESC
                    LIMIT 20
                """)
            ).fetchall()
            
            # Get error breakdown
            error_breakdown = db.session.execute(
                text("""
                    SELECT error_type, COUNT(*) as count
                    FROM debug_errors
                    WHERE resolved = 0
                    GROUP BY error_type
                    ORDER BY count DESC
                    LIMIT 20
                """)
            ).fetchall()
            
            analytics = {
                'recent_sessions_count': len(recent_sessions),
                'action_breakdown': [{'type': row[0], 'count': row[1]} for row in action_breakdown],
                'error_breakdown': [{'type': row[0], 'count': row[1]} for row in error_breakdown],
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error getting analytics: {e}")
            analytics = {}
        
        # Get AI insights
        ai_insights = {}
        try:
            all_intelligence = agent_ai_intelligence.get_all_intelligence()
            ai_insights = {
                'total_agents': all_intelligence.get('agents_count', 0),
                'total_decisions': all_intelligence.get('total_decisions', 0),
                'learning_entries': all_intelligence.get('total_learning_entries', 0)
            }
        except:
            pass
        
        response_payload = {
            'success': True,
            'analytics': analytics,
            'debugging': debugging_database.get_debugging_stats(),
            'profiles': browser_profile_tracker.get_profile_stats(),
            'ai_insights': ai_insights
        }
        response_payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_analytics_insights',
            user_prompt='Analyze debugging analytics trends and recommend actions.',
            context={
                'analytics': analytics,
                'ai_insights': ai_insights,
            },
        )
        response_payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(response_payload)
    except Exception as e:
        payload = {
            'success': True,
            'analytics': {},
            'debugging': {},
            'profiles': {},
            'ai_insights': {},
            'note': f'analytics fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='debugging_analytics_insights',
            user_prompt='Analyze degraded analytics state and propose safe recovery steps.',
            context={'error': str(e), 'status': 'degraded'},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200
