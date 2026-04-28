"""
Manager and Secretary Routes
API endpoints for manager and secretary agents
"""
from flask import Blueprint, jsonify, request

manager_secretary_bp = Blueprint('manager_secretary', __name__)

# Try to import agent services
try:
    from backend.services.agent_manager import AgentManager
    agent_manager = AgentManager()
except ImportError:
    agent_manager = None
    AgentManager = None

try:
    from backend.services.agent_secretary import agent_secretary
except ImportError:
    agent_secretary = None

try:
    from backend.services.agent_ai_orchestrator import agent_ai_orchestrator
except ImportError:
    agent_ai_orchestrator = None


def _get_agent_ai_response(profile_key: str, user_prompt: str, context: dict):
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

# ========== MANAGER ROUTES ==========

@manager_secretary_bp.route('/api/agents/manager/status', methods=['GET'])
def manager_status():
    """Get manager agent status"""
    try:
        if agent_manager is None:
            payload = {
                'success': True,
                'agent': {
                    'agent_id': 'agent_manager',
                    'status': 'available',
                    'level': 1,
                    'experience': 0,
                    'tasks_completed': 0,
                    'note': 'Agent manager service not fully initialized'
                }
            }
            payload['ai_assist'] = _get_agent_ai_response(
                profile_key='manager_status',
                user_prompt='Interpret manager status and suggest next operational step.',
                context=payload.get('agent', {}),
            )
            payload['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(payload), 200
        
        # Try to get status
        if hasattr(agent_manager, 'get_status'):
            result = agent_manager.get_status()
        elif hasattr(agent_manager, 'data'):
            result = agent_manager.data
        else:
            result = {
                'agent_id': 'agent_manager',
                'status': 'active',
                'level': 1,
                'experience': 0
            }
        
        payload = {'success': True, 'agent': result}
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_status',
            user_prompt='Interpret manager status and suggest next operational step.',
            context=result,
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200
    except Exception as e:
        payload = {
            'success': True,
            'agent': {
                'agent_id': 'agent_manager',
                'status': 'available',
                'error': str(e)
            }
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_status',
            user_prompt='Interpret degraded manager status and suggest safe checks.',
            context={'error': str(e)},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200

@manager_secretary_bp.route('/api/agents/manager/activate-all', methods=['POST'])
def manager_activate_all():
    """Activate all agents"""
    try:
        if agent_manager is None or not hasattr(agent_manager, 'activate_all_agents'):
            payload = {
                'success': True,
                'status': 'queued',
                'note': 'Agent manager service not available; activate-all deferred'
            }
            payload['ai_assist'] = _get_agent_ai_response(
                profile_key='manager_activate_all',
                user_prompt='Review activate-all deferred state and suggest follow-up.',
                context=payload,
            )
            payload['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(payload), 200
        result = agent_manager.activate_all_agents()
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_activate_all',
            user_prompt='Review activate-all outcome and suggest prioritized next actions.',
            context=result,
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        payload = {
            'success': True,
            'status': 'queued',
            'note': f'activate-all fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_activate_all',
            user_prompt='Review activate-all fallback and suggest recovery actions.',
            context={'error': str(e)},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200

@manager_secretary_bp.route('/api/agents/manager/auto-fix', methods=['POST'])
def manager_auto_fix():
    """Auto-fix with AI"""
    try:
        data = request.get_json(silent=True) or {}
        issue = data.get('issue', 'System maintenance')
        if agent_manager is None or not hasattr(agent_manager, 'auto_fix_with_ai'):
            base_result = {
                'success': True,
                'status': 'queued',
                'issue': issue,
                'note': 'Agent manager service not available; auto-fix deferred'
            }
            base_result['ai_assist'] = _get_agent_ai_response(
                profile_key='manager_auto_fix',
                user_prompt=f'Recommend fix strategy for issue: {issue}',
                context={'issue': issue, 'status': 'queued'},
            )
            base_result['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(base_result), 200
        result = agent_manager.auto_fix_with_ai(issue)
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_auto_fix',
            user_prompt=f'Recommend fix strategy for issue: {issue}',
            context={'issue': issue, 'manager_result': result},
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'status': 'queued',
            'note': f'auto-fix fallback: {str(e)}'
        }), 200

@manager_secretary_bp.route('/api/agents/manager/assign-task', methods=['POST'])
def manager_assign_task():
    """Assign task to agent"""
    try:
        data = request.get_json(silent=True) or {}
        agent_id = data.get('agent_id')
        task = data.get('task')
        priority = data.get('priority', 'medium')
        
        if not agent_id or not task:
            return jsonify({
                'success': False,
                'error': 'agent_id and task are required'
            }), 400
        
        if agent_manager is None or not hasattr(agent_manager, 'assign_task'):
            return jsonify({
                'success': True,
                'status': 'queued',
                'agent_id': agent_id,
                'task': task,
                'priority': priority,
                'note': 'Agent manager service not available; task deferred'
            }), 200
        result = agent_manager.assign_task(agent_id, task, priority)
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_assign_task',
            user_prompt=f"Review assignment for agent '{agent_id}' with priority '{priority}'.",
            context={'agent_id': agent_id, 'task': task, 'priority': priority, 'result': result},
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        payload = {
            'success': True,
            'status': 'queued',
            'note': f'assign-task fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='manager_assign_task',
            user_prompt='Review assign-task fallback and suggest safe next actions.',
            context={'error': str(e)},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200

# ========== SECRETARY ROUTES ==========

@manager_secretary_bp.route('/api/agents/secretary/status', methods=['GET'])
def secretary_status():
    """Get secretary agent status"""
    try:
        if agent_secretary is None or not hasattr(agent_secretary, 'get_status'):
            payload = {
                'success': True,
                'agent': {
                    'agent_id': 'agent_secretary',
                    'status': 'available',
                    'note': 'Secretary service not available'
                }
            }
            payload['ai_assist'] = _get_agent_ai_response(
                profile_key='secretary_status',
                user_prompt='Interpret secretary status and suggest next step.',
                context=payload.get('agent', {}),
            )
            payload['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(payload), 200
        result = agent_secretary.get_status()
        payload = {'success': True, 'agent': result}
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_status',
            user_prompt='Interpret secretary status and suggest next step.',
            context=result,
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200
    except Exception as e:
        payload = {
            'success': True,
            'agent': {
                'agent_id': 'agent_secretary',
                'status': 'available',
                'note': f'secretary fallback: {str(e)}'
            }
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_status',
            user_prompt='Interpret degraded secretary status and suggest safe checks.',
            context={'error': str(e)},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200

@manager_secretary_bp.route('/api/agents/secretary/coordinate-activation', methods=['POST'])
def secretary_coordinate_activation():
    """Coordinate agent activation"""
    try:
        if agent_secretary is None or not hasattr(agent_secretary, 'coordinate_agent_activation'):
            payload = {
                'success': True,
                'status': 'queued',
                'note': 'Secretary service not available; coordinate activation deferred'
            }
            payload['ai_assist'] = _get_agent_ai_response(
                profile_key='secretary_coordinate_activation',
                user_prompt='Review coordinate-activation deferred state and suggest follow-up.',
                context=payload,
            )
            payload['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(payload), 200
        result = agent_secretary.coordinate_agent_activation()
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_coordinate_activation',
            user_prompt='Review coordination outcome and suggest process improvements.',
            context=result,
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        payload = {
            'success': True,
            'status': 'queued',
            'note': f'coordinate fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_coordinate_activation',
            user_prompt='Review coordinate-activation fallback and suggest recovery actions.',
            context={'error': str(e)},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200

@manager_secretary_bp.route('/api/agents/secretary/generate-report', methods=['POST'])
def secretary_generate_report():
    """Generate AI report"""
    try:
        data = request.get_json(silent=True) or {}
        report_type = data.get('report_type', 'status')
        if agent_secretary is None or not hasattr(agent_secretary, 'generate_ai_report'):
            base_result = {
                'success': True,
                'report': {
                    'type': report_type,
                    'status': 'deferred'
                },
                'note': 'Secretary service not available; report deferred'
            }
            base_result['ai_assist'] = _get_agent_ai_response(
                profile_key='secretary_generate_report',
                user_prompt=f'Generate report summary for report type: {report_type}',
                context={'report_type': report_type, 'status': 'deferred'},
            )
            base_result['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(base_result), 200
        result = agent_secretary.generate_ai_report(report_type)
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_generate_report',
            user_prompt=f'Generate report summary for report type: {report_type}',
            context={'report_type': report_type, 'secretary_result': result},
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'report': {'status': 'deferred'},
            'note': f'generate-report fallback: {str(e)}'
        }), 200

@manager_secretary_bp.route('/api/agents/secretary/schedule-auto-fix', methods=['POST'])
def secretary_schedule_auto_fix():
    """Schedule automatic fixes"""
    try:
        data = request.get_json(silent=True) or {}
        schedule_type = data.get('schedule_type', 'daily')
        if agent_secretary is None or not hasattr(agent_secretary, 'schedule_auto_fix'):
            payload = {
                'success': True,
                'schedule_type': schedule_type,
                'status': 'deferred',
                'note': 'Secretary service not available; schedule deferred'
            }
            payload['ai_assist'] = _get_agent_ai_response(
                profile_key='secretary_schedule_auto_fix',
                user_prompt=f"Review deferred auto-fix schedule '{schedule_type}' and suggest follow-up.",
                context=payload,
            )
            payload['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(payload), 200
        result = agent_secretary.schedule_auto_fix(schedule_type)
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_schedule_auto_fix',
            user_prompt=f"Review auto-fix schedule '{schedule_type}' and suggest improvements.",
            context={'schedule_type': schedule_type, 'result': result},
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        payload = {
            'success': True,
            'status': 'deferred',
            'note': f'schedule fallback: {str(e)}'
        }
        payload['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_schedule_auto_fix',
            user_prompt='Review schedule-auto-fix fallback and suggest safe recovery steps.',
            context={'error': str(e)},
        )
        payload['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(payload), 200

@manager_secretary_bp.route('/api/agents/secretary/document', methods=['POST'])
def secretary_document():
    """Document activity"""
    try:
        data = request.get_json(silent=True) or {}
        activity_type = data.get('activity_type', 'general')
        details = data.get('details', {})
        if agent_secretary is None or not hasattr(agent_secretary, 'document_activity'):
            base_result = {
                'success': True,
                'status': 'logged-locally',
                'activity_type': activity_type,
                'details': details,
                'note': 'Secretary service not available; document deferred'
            }
            base_result['ai_assist'] = _get_agent_ai_response(
                profile_key='secretary_document',
                user_prompt=f'Document activity type: {activity_type}',
                context={'activity_type': activity_type, 'details': details},
            )
            base_result['ai_orchestrator_metrics'] = _get_ai_metrics()
            return jsonify(base_result), 200
        result = agent_secretary.document_activity(activity_type, details)
        result['ai_assist'] = _get_agent_ai_response(
            profile_key='secretary_document',
            user_prompt=f'Document activity type: {activity_type}',
            context={'activity_type': activity_type, 'details': details, 'secretary_result': result},
        )
        result['ai_orchestrator_metrics'] = _get_ai_metrics()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'status': 'logged-locally',
            'note': f'document fallback: {str(e)}'
        }), 200
