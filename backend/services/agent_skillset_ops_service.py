"""
Operational passes for agent skillsets: blueprint/route fixer (Register Intelligence) and API service scans.
Logs to logs/agent_cron/ — wired from agent_cron_service and cron scripts.
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _append_jsonl(filename: str, payload: Dict[str, Any]) -> str:
    log_dir = os.path.join(BASE_DIR, 'logs', 'agent_cron')
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, filename)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    return path


def run_blueprint_route_fixer_job() -> Dict[str, Any]:
    """
    Full Register Intelligence audit (blueprints, backend routes, frontend API gaps).
    Dry-run only; does not modify register_blueprints.py unless future tooling applies patches.
    """
    from backend.services.register_intelligence import run_register_intelligence

    report = run_register_intelligence(project_root=BASE_DIR, dry_run=True, discover_only=False)
    audit = report.get('audit', {}) or {}
    summary = audit.get('summary', {})
    payload = {
        'job': 'blueprint_route_fixer',
        'at': datetime.now(timezone.utc).isoformat(),
        'summary': summary,
        'potential_missing_sample': (report.get('discovery') or {}).get('potential_missing', [])[:20],
    }
    path = _append_jsonl('blueprint_route_fixer.jsonl', payload)
    ai_summary = None
    try:
        from backend.services.agent_ai_intelligence import agent_ai_intelligence
        ai_summary = agent_ai_intelligence.llm_insight(
            'blueprint_route_fixer_agent',
            topic='register_intelligence_audit',
            context={'summary': summary, 'missing_sample': payload.get('potential_missing_sample')},
            task_type='log_triage',
        )
    except Exception:
        ai_summary = {'success': False, 'error': 'llm_insight_unavailable'}
    return {
        'success': True,
        'log_path': path,
        'summary': summary,
        'ai_summary': ai_summary,
    }


def run_api_service_skill_job() -> Dict[str, Any]:
    """
    API-focused discovery: frontend API call count vs backend routes, gap count.
    Uses RegisterIntelligence.discover_all() (lighter than re-running full audit object twice).
    """
    from backend.services.register_intelligence.orchestrator import RegisterIntelligence

    ri = RegisterIntelligence(project_root=BASE_DIR, dry_run=True)
    disc = ri.discover_all()
    missing = disc.get('potential_missing') or []
    summary = {
        'blueprints_count': disc.get('blueprints_count'),
        'backend_routes_count': disc.get('backend_routes_count'),
        'frontend_api_count': disc.get('frontend_api_count'),
        'potential_missing_count': len(missing),
    }
    payload = {
        'job': 'api_service_skill',
        'at': datetime.now(timezone.utc).isoformat(),
        'summary': summary,
        'potential_missing_sample': list(missing)[:25],
    }
    path = _append_jsonl('api_service_skill.jsonl', payload)
    ai_summary = None
    try:
        from backend.services.agent_ai_intelligence import agent_ai_intelligence
        ai_summary = agent_ai_intelligence.llm_insight(
            'api_service_agent',
            topic='api_service_gap_scan',
            context=summary,
            task_type='debugger_challenge',
        )
    except Exception:
        ai_summary = {'success': False, 'error': 'llm_insight_unavailable'}
    return {
        'success': True,
        'log_path': path,
        'summary': summary,
        'ai_summary': ai_summary,
    }
