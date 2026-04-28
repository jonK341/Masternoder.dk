"""
Agent Profile Routes
Provides endpoints for user agent progress, activity feed, and skill management.
Connected to agent_db_service (DB-backed with file fallback).
"""
import os

from flask import Blueprint, jsonify, request, session

agent_profile_bp = Blueprint('agent_profile', __name__)


def _resolve():
    """Resolve user_id: session > body > query > default_user."""
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        pass
    # Inline fallback
    if session.get('user_id'):
        return str(session['user_id']).strip()
    try:
        data = request.get_json(silent=True) or {}
        uid = data.get('user_id') or request.args.get('user_id')
        if uid and str(uid).strip() and str(uid).strip().lower() != 'default_user':
            return str(uid).strip()
    except Exception:
        pass
    return 'default_user'


@agent_profile_bp.route('/api/agents/my-agents', methods=['GET'])
def get_my_agents():
    """Return all agents assigned to the current user with progress (level, XP, skills, last action)."""
    user_id = _resolve()
    try:
        from backend.services.agent_db_service import agent_db_service
        agents = agent_db_service.get_user_agents(user_id)
        return jsonify({'success': True, 'user_id': user_id, 'agents': agents}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'agents': []}), 200


@agent_profile_bp.route('/api/agents/activity-feed', methods=['GET'])
def get_agent_activity_feed():
    """Return recent agent activity for the current user."""
    user_id = _resolve()
    limit = min(100, max(1, int(request.args.get('limit', 30))))
    try:
        from backend.services.agent_db_service import agent_db_service
        activities = agent_db_service.get_activity_feed(user_id, limit=limit)
        return jsonify({'success': True, 'user_id': user_id, 'activities': activities}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e), 'activities': []}), 200


@agent_profile_bp.route('/api/agents/sync', methods=['POST'])
def sync_agent_progress():
    """Sync agent assignments from JSON files into the DB (idempotent)."""
    user_id = _resolve()
    try:
        from backend.services.agent_db_service import agent_db_service
        synced = agent_db_service.sync_user_agents_to_db(user_id)
        return jsonify({'success': True, 'user_id': user_id, 'rows_synced': synced}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200


@agent_profile_bp.route('/api/agents/follow-action', methods=['POST'])
def record_follow_action():
    """
    Record that an agent followed the user's action. Optional win=True awards extra XP.
    Body: { "user_action": "generated_video" | "quest_done" | "battle_won" | ..., "win": false, "agent_id": null }.
    When agent_id is omitted, the first assigned agent (or learning_agent) is used.
    """
    user_id = _resolve()
    data = request.get_json() or {}
    user_action = data.get('user_action', 'user_action')
    win = bool(data.get('win', False))
    agent_id = data.get('agent_id') or ''
    try:
        from backend.services.agent_db_service import agent_db_service
        from backend.services.user_agent_skills import user_agent_skills
        if not agent_id:
            skills_data = user_agent_skills.get_user_skills(user_id)
            assigned = skills_data.get('assigned_agents', [])
            agent_id = next((a for a in assigned if 'learning' in a), assigned[0] if assigned else 'learning_agent')
        result = agent_db_service.record_user_action_followed(
            user_id=user_id, agent_id=agent_id,
            user_action=user_action, win=win,
            xp_on_win=int(data.get('xp_on_win', 25)),
            points_on_win=float(data.get('points_on_win', 5.0)),
            metadata=data.get('metadata'),
        )
        return jsonify({'success': True, 'agent_id': agent_id, 'win': win, **result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200


@agent_profile_bp.route('/api/agents/record-action', methods=['POST'])
def record_agent_action():
    """Manually record an agent action (for testing or external triggers)."""
    user_id = _resolve()
    data = request.get_json() or {}
    agent_id = data.get('agent_id', '')
    action = data.get('action', 'skill_execution')
    skill = data.get('skill')
    xp = int(data.get('xp_gained', 5))
    pts = float(data.get('points_gained', 0))
    metadata = data.get('metadata', {})
    if not agent_id:
        return jsonify({'success': False, 'error': 'agent_id required'}), 400
    try:
        from backend.services.agent_db_service import agent_db_service
        result = agent_db_service.record_agent_activity(
            user_id=user_id, agent_id=agent_id, action=action,
            skill=skill, xp_gained=xp, points_gained=pts, metadata=metadata
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200


@agent_profile_bp.route('/api/agents/skill-levelup', methods=['POST'])
def skill_levelup():
    """Trigger XP for a user skill and record agent activity."""
    user_id = _resolve()
    data = request.get_json() or {}
    agent_id = data.get('agent_id', '')
    skill_name = data.get('skill', '')
    xp = int(data.get('xp', 50))
    if not agent_id or not skill_name:
        return jsonify({'success': False, 'error': 'agent_id and skill required'}), 400
    try:
        from backend.services.user_agent_skills import user_agent_skills
        from backend.services.agent_db_service import agent_db_service
        skill_result = user_agent_skills.level_up_skill(user_id, skill_name, experience=xp)
        agent_db_service.record_agent_activity(
            user_id=user_id, agent_id=agent_id, action='skill_execution',
            skill=skill_name, xp_gained=xp, metadata={'skill_result': skill_result}
        )
        return jsonify({'success': True, 'skill_result': skill_result}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200


@agent_profile_bp.route('/api/agents/tech-unlock', methods=['POST'])
def tech_unlock_skill():
    """
    Called when a user unlocks an agent technology.
    Adds a new skill to their primary assigned agent and records activity.
    """
    user_id = _resolve()
    data = request.get_json() or {}
    tech_id = data.get('tech_id', '')
    tech_name = data.get('tech_name', tech_id)
    if not tech_id:
        return jsonify({'success': False, 'error': 'tech_id required'}), 400
    try:
        from backend.services.user_agent_skills import user_agent_skills
        from backend.services.agent_db_service import agent_db_service

        skills_data = user_agent_skills.get_user_skills(user_id)
        assigned = skills_data.get('assigned_agents', [])
        target_agent = assigned[0] if assigned else 'content_generator_agent'

        skill_name = f"tech_{tech_id}"
        user_agent_skills.add_skill(user_id, target_agent, skill_name, level=1)

        agent_db_service.record_agent_activity(
            user_id=user_id, agent_id=target_agent,
            action='tech_unlocked', skill=skill_name,
            xp_gained=25, points_gained=10,
            metadata={'tech_id': tech_id, 'tech_name': tech_name}
        )
        return jsonify({'success': True, 'agent_id': target_agent, 'skill_added': skill_name}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 200


def _reporter_token_ok() -> bool:
    secret = (os.environ.get('KNOWLEDGE_REPORT_SECRET') or '').strip()
    if not secret:
        return False
    token = (request.headers.get('X-Reporter-Token') or request.args.get('token') or '').strip()
    return token == secret


@agent_profile_bp.route('/api/agents/reporter/knowledge-ingredients', methods=['GET', 'POST'])
def reporter_knowledge_ingredients():
    """
    Reporter agent: build news-report ingredients for knowledge sharing (compendium / broadcast).
    Optional auth: KNOWLEDGE_REPORT_SECRET with X-Reporter-Token or ?token= (for cron).
    If the secret is unset, the endpoint is open (set the secret in production).
    """
    secret_set = bool((os.environ.get('KNOWLEDGE_REPORT_SECRET') or '').strip())
    if secret_set and not _reporter_token_ok():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401

    try:
        from backend.services.knowledge_sharing_report_service import (
            build_knowledge_ingredients,
            append_ingredients_log,
        )
        from backend.services.agent_db_service import agent_db_service

        payload = build_knowledge_ingredients()
        log_path = None
        if request.args.get('append_log') == '1' or (request.get_json(silent=True) or {}).get('append_log'):
            log_path = append_ingredients_log(payload)

        data = request.get_json(silent=True) or {}
        uid = data.get('user_id') or request.args.get('user_id') or 'platform_knowledge'
        record = data.get('record_activity', request.args.get('record_activity'))
        if record in (True, '1', 'true'):
            agent_db_service.record_agent_activity(
                user_id=str(uid),
                agent_id='reporter_agent',
                action='news_report_ingredients',
                skill='broadcast',
                xp_gained=5,
                metadata={'ingredient_count': len(payload.get('ingredients') or [])},
            )

        out = {'success': True, 'report': payload}
        if log_path:
            out['log_path'] = log_path
        return jsonify(out), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_profile_bp.route('/api/agents/user-skills/maintenance-inactive', methods=['POST'])
def user_skills_maintenance_inactive():
    """
    Batch-remove stale user_agent_skills JSON files (default 10 per run). Requires USER_SKILLS_MAINTENANCE_SECRET
    if set; if unset, rejects in production (FLASK_ENV=production or PRODUCTION=true).
    Body/query: dry_run=1, max_batch=10, inactive_days=120
    """
    dry_run = request.args.get('dry_run') in ('1', 'true', 'True') or (request.get_json(silent=True) or {}).get('dry_run') in (True, '1')
    try:
        max_batch = int(request.args.get('max_batch') or (request.get_json(silent=True) or {}).get('max_batch') or 10)
    except Exception:
        max_batch = 10
    try:
        inactive_days = (request.get_json(silent=True) or {}).get('inactive_days')
        if inactive_days is None:
            inactive_days = request.args.get('inactive_days')
        inactive_days = int(inactive_days) if inactive_days is not None else None
    except Exception:
        inactive_days = None

    maint_secret = (os.environ.get('USER_SKILLS_MAINTENANCE_SECRET') or '').strip()
    prod = (os.environ.get('FLASK_ENV') == 'production') or (str(os.environ.get('PRODUCTION', '')).lower() in ('1', 'true', 'yes'))
    token = (request.headers.get('X-Maintenance-Token') or request.args.get('token') or '').strip()
    if maint_secret:
        if token != maint_secret:
            return jsonify({'success': False, 'error': 'unauthorized'}), 401
    elif prod:
        return jsonify({'success': False, 'error': 'maintenance_secret_required_in_production'}), 401

    try:
        from backend.services.user_agent_skills import user_agent_skills
        result = user_agent_skills.maintenance_inactive_user_skills(
            max_batch=max(1, min(500, max_batch)),
            inactive_days=inactive_days,
            dry_run=dry_run,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
