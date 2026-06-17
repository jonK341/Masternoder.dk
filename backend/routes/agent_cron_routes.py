"""
Secured cron entrypoints for agent platform tasks (skillsets, maintenance, research, LLM snapshot).
See docs/RESEARCH_AI_SYSTEMS.md — Agent cron jobs.
"""
import os

from flask import Blueprint, jsonify, request

agent_cron_bp = Blueprint('agent_cron', __name__)


def _cron_secrets_configured() -> bool:
    return bool(
        (os.environ.get('AGENT_CRON_SECRET') or '').strip()
        or (os.environ.get('MN2_OPS_SECRET') or '').strip()
        or (os.environ.get('MN2_SCAN_SECRET') or '').strip()
    )


def _agent_cron_authorized() -> bool:
    cron_secret = (os.environ.get('AGENT_CRON_SECRET') or '').strip()
    tok = (request.headers.get('X-Agent-Cron-Token') or request.args.get('token') or '').strip()
    if cron_secret and tok == cron_secret:
        return True
    ops_secret = (
        (os.environ.get('MN2_OPS_SECRET') or '').strip()
        or (os.environ.get('MN2_SCAN_SECRET') or '').strip()
    )
    ops_hdr = (request.headers.get('X-Ops-Secret') or '').strip()
    if ops_secret and ops_hdr == ops_secret:
        return True
    if not _cron_secrets_configured():
        return request.environ.get('REMOTE_ADDR') in ('127.0.0.1', '::1')
    return False


def _is_production() -> bool:
    return (os.environ.get('FLASK_ENV') == 'production') or (
        str(os.environ.get('PRODUCTION', '')).lower() in ('1', 'true', 'yes')
    )


def _parse_jobs() -> list:
    data = request.get_json(silent=True) or {}
    raw = data.get('jobs')
    if raw is None:
        raw = request.args.get('jobs')
    if isinstance(raw, str):
        preset = raw.strip().lower()
        if preset in (
            'daily', 'weekly', 'monthly', 'knowledge',
            'blueprint_route', 'api_service', 'routes', 'casino', 'camgirls', 'trader',
        ):
            from backend.services.agent_cron_service import expand_preset
            return expand_preset(preset)
        return [j.strip() for j in raw.split(',') if j.strip()]
    if isinstance(raw, list):
        return [str(j).strip() for j in raw if str(j).strip()]
    return []


@agent_cron_bp.route('/api/agents/cron/run', methods=['POST'])
def agents_cron_run():
    """
    Run agent cron jobs (requires AGENT_CRON_SECRET, or X-Ops-Secret with MN2_OPS_SECRET / MN2_SCAN_SECRET).
    Query/body: jobs=daily | weekly | monthly | knowledge | blueprint_route | api_service | routes | trader | agent_trader | comma-separated.
    Jobs: skillsets_ensure, skillsets_rebalance, user_skills_maintenance, knowledge_ingredients,
          automation_maintenance, agent_health_check, research_rotation, llm_status_snapshot,
          blueprint_route_fixer, api_service_skill
    Optional: maintenance_max_batch, inactive_days, append_knowledge_log, record_reporter_activity
    """
    if not _agent_cron_authorized():
        if _is_production() and not _cron_secrets_configured():
            return jsonify({'success': False, 'error': 'AGENT_CRON_SECRET not configured'}), 503
        return jsonify({'success': False, 'error': 'unauthorized'}), 401

    jobs = _parse_jobs()
    if not jobs:
        return jsonify({
            'success': False,
            'error': 'no jobs: use jobs=daily|weekly|monthly|knowledge|blueprint_route|api_service|routes or a list',
        }), 400

    data = request.get_json(silent=True) or {}
    try:
        mbatch = int(data.get('maintenance_max_batch') or request.args.get('maintenance_max_batch') or 10)
    except Exception:
        mbatch = 10
    try:
        inactive = data.get('inactive_days') or request.args.get('inactive_days')
        inactive = int(inactive) if inactive is not None and str(inactive).strip() != '' else None
    except Exception:
        inactive = None
    append_log = (request.args.get('append_knowledge_log') == '1') or data.get('append_knowledge_log') is True
    record_rep = (request.args.get('record_reporter_activity') == '1') or data.get('record_reporter_activity') is True
    try:
        rt = int(data.get('rebalance_target_total') or request.args.get('rebalance_target_total') or 500000)
    except Exception:
        rt = 500000

    try:
        from backend.services.agent_cron_service import run_agent_cron_jobs
        result = run_agent_cron_jobs(
            jobs,
            maintenance_max_batch=max(1, min(500, mbatch)),
            inactive_days=inactive,
            append_knowledge_log=append_log,
            record_reporter_activity=record_rep,
            rebalance_target_total=rt,
        )
        status = 200 if result.get('success') and not result.get('errors') else 207
        return jsonify(result), status
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_cron_bp.route('/api/agents/cron/presets', methods=['GET'])
def agents_cron_presets():
    """Describe named presets (no secret required)."""
    from backend.services.agent_cron_service import expand_preset

    return jsonify({
        'success': True,
        'presets': {
            'daily': expand_preset('daily'),
            'weekly': expand_preset('weekly'),
            'monthly': expand_preset('monthly'),
            'knowledge': expand_preset('knowledge'),
            'blueprint_route': expand_preset('blueprint_route'),
            'api_service': expand_preset('api_service'),
            'routes': expand_preset('routes'),
            'casino': expand_preset('casino'),
            'camgirls': expand_preset('camgirls'),
            'trader': expand_preset('trader'),
        },
    }), 200
