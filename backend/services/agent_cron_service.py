"""
Agent platform cron jobs — skillsets, maintenance, research, LLM health (see docs/RESEARCH_AI_SYSTEMS.md §Agent cron).
"""
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Rotating research topics (agent_research_tracker) — aligns with RESEARCH_AI_SYSTEMS §4
_RESEARCH_TOPIC_IDS = [
    'api_structure',
    'performance',
    'security',
    'point_systems',
    'user_engagement',
    'code_quality',
    'trigger_optimization',
]


def _log_dir() -> str:
    d = os.path.join(BASE_DIR, 'logs', 'agent_cron')
    os.makedirs(d, exist_ok=True)
    return d


def _append_jsonl(name: str, payload: Dict[str, Any]) -> str:
    path = os.path.join(_log_dir(), name)
    with open(path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    return path


def run_agent_cron_jobs(
    jobs: List[str],
    *,
    maintenance_max_batch: int = 10,
    inactive_days: Optional[int] = None,
    append_knowledge_log: bool = False,
    record_reporter_activity: bool = False,
    rebalance_target_total: int = 500_000,
) -> Dict[str, Any]:
    """
    Run named jobs. Each job is independent; failures are captured per key.
    """
    out: Dict[str, Any] = {
        'success': True,
        'ran_at': datetime.now(timezone.utc).isoformat(),
        'jobs': jobs,
        'results': {},
        'errors': {},
    }

    for job in jobs:
        try:
            if job == 'skillsets_ensure':
                from backend.services.agent_skillset import agent_skillset
                out['results'][job] = {
                    'battle': agent_skillset.ensure_battle_skills_per_agent(count=30),
                    'sales': agent_skillset.ensure_sales_skillsets_per_agent(count=50),
                    'paypal': agent_skillset.ensure_paypal_skillsets_per_agent(count=15),
                    'top25': agent_skillset.ensure_top25_skill_upgrades_per_agent(count=25),
                    'shared_growth': agent_skillset.ensure_shared_growth_skills(count=100),
                    'blueprint_route_fixer': agent_skillset.ensure_blueprint_route_fixer_skills_per_agent(),
                    'api_service': agent_skillset.ensure_api_service_skills_per_agent(),
                }
            elif job == 'skillsets_rebalance':
                from backend.services.agent_skillset import agent_skillset
                out['results'][job] = agent_skillset.rebalance_unique_skill_values(
                    target_total=rebalance_target_total
                )
            elif job == 'user_skills_maintenance':
                from backend.services.user_agent_skills import user_agent_skills
                out['results'][job] = user_agent_skills.maintenance_inactive_user_skills(
                    max_batch=maintenance_max_batch,
                    inactive_days=inactive_days,
                    dry_run=False,
                )
            elif job == 'knowledge_ingredients':
                from backend.services.knowledge_sharing_report_service import (
                    build_knowledge_ingredients,
                    append_ingredients_log,
                )
                from backend.services.agent_db_service import agent_db_service

                payload = build_knowledge_ingredients()
                log_path = None
                if append_knowledge_log:
                    log_path = append_ingredients_log(payload)
                if record_reporter_activity:
                    agent_db_service.record_agent_activity(
                        user_id='platform_knowledge',
                        agent_id='reporter_agent',
                        action='news_report_ingredients',
                        skill='broadcast',
                        xp_gained=5,
                        metadata={'cron': True, 'ingredient_count': len(payload.get('ingredients') or [])},
                    )
                out['results'][job] = {'report': payload, 'ingredients_log': log_path}
            elif job == 'automation_maintenance':
                from backend.services.agent_automation import agent_automation
                agent_automation._run_maintenance_tasks()
                out['results'][job] = {'ok': True}
            elif job == 'agent_health_check':
                from backend.services.master_fix_agent_skills import master_fix_agent_skills
                out['results'][job] = master_fix_agent_skills.skill_monitor_system_health()
            elif job == 'research_rotation':
                from backend.services.agent_research_tracker import agent_research_tracker
                idx = datetime.now(timezone.utc).timetuple().tm_yday % len(_RESEARCH_TOPIC_IDS)
                topic_id = _RESEARCH_TOPIC_IDS[idx]
                started = agent_research_tracker.start_research(
                    topic_id, agent_id='ai_intelligence_agent'
                )
                insight = None
                if started.get('success'):
                    try:
                        from backend.services.agent_ai_intelligence import agent_ai_intelligence
                        insight = agent_ai_intelligence.llm_insight(
                            'ai_intelligence_agent',
                            topic=f'research_rotation:{topic_id}',
                            context={'project': started.get('project'), 'topic_id': topic_id},
                            task_type='context',
                        )
                    except Exception:
                        insight = {'success': False, 'error': 'llm_insight_failed'}
                out['results'][job] = {'started': started, 'llm_insight': insight}
            elif job == 'llm_status_snapshot':
                from backend.services.llm_service import get_provider_status
                snap = {
                    'at': datetime.now(timezone.utc).isoformat(),
                    'providers': get_provider_status(),
                }
                path = _append_jsonl('llm_provider_status.jsonl', snap)
                out['results'][job] = {'snapshot_path': path, 'provider_count': len(snap.get('providers') or [])}
            elif job == 'blueprint_route_fixer':
                from backend.services.agent_skillset_ops_service import run_blueprint_route_fixer_job
                out['results'][job] = run_blueprint_route_fixer_job()
            elif job == 'api_service_skill':
                from backend.services.agent_skillset_ops_service import run_api_service_skill_job
                out['results'][job] = run_api_service_skill_job()
            elif job == 'casino_agents':
                from backend.services import casino_agents_service
                from backend.services.agent_skillset import agent_skillset
                skill_sync = agent_skillset.ensure_casino_agent_skillsets()
                play = casino_agents_service.run_all(dry_run=False)
                out['results'][job] = {'skill_sync': skill_sync, 'play': play}
            elif job == 'casino_agent_skillsets':
                from backend.services.agent_skillset import agent_skillset
                out['results'][job] = agent_skillset.ensure_casino_agent_skillsets()
            elif job == 'camgirls_agent_skillsets':
                from backend.services.agent_skillset import agent_skillset
                out['results'][job] = agent_skillset.ensure_camgirls_agent_skillsets()
            elif job == 'agent_trader':
                from backend.services.agent_trader_service import run_all_traders
                out['results'][job] = run_all_traders()
            elif job == 'agent_treasury_distribute':
                from backend.services.agent_wallet_service import distribute_agent_funding
                out['results'][job] = distribute_agent_funding()
            elif job == 'monetization_allowance_nudges':
                from backend.services.monetization_allowance_service import run_allowance_nudge_scan
                out['results'][job] = run_allowance_nudge_scan()
            elif job == 'monetization_renewal_emails':
                from backend.services.monetization_email_service import run_renewal_reminder_emails
                out['results'][job] = run_renewal_reminder_emails()
            elif job == 'monetization_weekly_revenue_pulse':
                from backend.services.monetization_revenue_pulse_service import run_weekly_revenue_pulse
                out['results'][job] = run_weekly_revenue_pulse()
            else:
                out['errors'][job] = f'unknown_job:{job}'
                out['success'] = False
        except Exception as e:
            out['errors'][job] = str(e)[:500]
            out['success'] = False

    if out['errors']:
        out['success'] = False

    return out


def expand_preset(name: str) -> List[str]:
    """Named bundles for cron scripts (see RESEARCH_AI_SYSTEMS.md)."""
    n = (name or '').strip().lower()
    if n == 'daily':
        return [
            'user_skills_maintenance',
            'automation_maintenance',
            'llm_status_snapshot',
        ]
    if n == 'weekly':
        return [
            'skillsets_ensure',
            'agent_health_check',
            'research_rotation',
        ]
    if n == 'monthly':
        return ['skillsets_rebalance']
    if n == 'knowledge':
        return ['knowledge_ingredients']
    if n == 'blueprint_route':
        return ['blueprint_route_fixer']
    if n == 'api_service':
        return ['api_service_skill']
    if n == 'routes':
        return ['blueprint_route_fixer', 'api_service_skill']
    if n == 'casino':
        return ['casino_agent_skillsets', 'casino_agents']
    if n == 'camgirls':
        return ['camgirls_agent_skillsets']
    if n == 'trader':
        return ['agent_trader']
    return []
