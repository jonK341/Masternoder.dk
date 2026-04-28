"""
Agent Automation Routes
API endpoints for agent automation and groups
"""
from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime
from backend.services.agent_automation import agent_automation
from backend.services.agent_skillset import agent_skillset
from backend.services.agent_groups import agent_groups
from backend.services.agent_ability_tracker import agent_ability_tracker

agent_automation_bp = Blueprint('agent_automation', __name__)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Auto-start automation on import (omit when AGENT_DAEMON_CONTROLS_AUTOMATION=1 + scripts/agent_daemon.py)
if os.environ.get('AGENT_DAEMON_CONTROLS_AUTOMATION', '').strip().lower() not in ('1', 'true', 'yes'):
    try:
        agent_automation.config['enabled'] = True
        agent_automation.config['autoplay'] = True
        agent_automation.save_config()
        agent_automation.start()
        print("[AgentAutomation] Auto-started and enabled")
    except Exception as e:
        print(f"[WARN] AgentAutomation auto-start failed: {e}")
else:
    print("[AgentAutomation] External daemon mode — tick via POST /api/agents/daemon/tick")

# ========== AUTOMATION ENDPOINTS ==========

@agent_automation_bp.route('/api/agent/automation/status', methods=['GET'])
def get_automation_status():
    """Get automation status"""
    try:
        status = agent_automation.get_status()
        return jsonify({
            'success': True,
            'status': status
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/automation/start', methods=['POST'])
def start_automation():
    """Start automation"""
    try:
        agent_automation.start()
        return jsonify({
            'success': True,
            'message': 'Automation started'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/automation/stop', methods=['POST'])
def stop_automation():
    """Stop automation"""
    try:
        agent_automation.stop()
        return jsonify({
            'success': True,
            'message': 'Automation stopped'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/automation/maintenance', methods=['POST'])
def run_maintenance():
    """Run maintenance tasks"""
    try:
        agent_automation._run_maintenance_tasks()
        return jsonify({
            'success': True,
            'message': 'Maintenance completed'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/automation/health-check', methods=['POST'])
def health_check():
    """Run health check"""
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        result = master_fix_agent_skills.skill_monitor_system_health()
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== SKILLSET ENDPOINTS ==========

@agent_automation_bp.route('/api/agent/skillset/<agent_id>', methods=['GET'])
def get_skillset(agent_id):
    """Get skillset for an agent"""
    try:
        agent_type = request.args.get('type', 'agents')
        skillset = agent_skillset.get_skillset(agent_id, agent_type)
        return jsonify({
            'success': True,
            'skillset': skillset
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/skillset/<agent_id>/add-skill', methods=['POST'])
def add_skill(agent_id):
    """Add skill to agent"""
    try:
        data = request.get_json() or {}
        skill = data.get('skill')
        agent_type = data.get('type', 'agents')
        
        if not skill:
            return jsonify({
                'success': False,
                'error': 'Skill name required'
            }), 400
        
        agent_skillset.add_skill(agent_id, skill, agent_type)
        return jsonify({
            'success': True,
            'message': f'Skill {skill} added to {agent_id}'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/skillset/all', methods=['GET'])
@agent_automation_bp.route('/api/agent-skillset/all', methods=['GET'])  # Front page uses this path
@agent_automation_bp.route('/api/agents/skillsets/all', methods=['GET'])  # Alternative route
def get_all_skillsets():
    """Get all skillsets"""
    try:
        skillsets = agent_skillset.get_all_skillsets()
        return jsonify({
            'success': True,
            'skillsets': skillsets
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/skillset/stats', methods=['GET'])
@agent_automation_bp.route('/api/agents/skillsets/stats', methods=['GET'])  # Alternative route
def get_skillset_stats():
    """Get skillset statistics"""
    try:
        stats = agent_skillset.get_skillset_stats()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_automation_bp.route('/api/agents/skillsets/rebalance', methods=['POST'])
def rebalance_unique_skill_values():
    """Rebalance unique skill value points per agent."""
    try:
        data = request.get_json(silent=True) or {}
        target_total = int(data.get('target_total', 500000))
        result = agent_skillset.rebalance_unique_skill_values(target_total=target_total)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/battle/ensure', methods=['POST'])
def ensure_battle_skills():
    """Ensure battle skills per agent."""
    try:
        data = request.get_json(silent=True) or {}
        per_agent = int(data.get('per_agent', 30))
        result = agent_skillset.ensure_battle_skills_per_agent(count=per_agent)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/sales/ensure', methods=['POST'])
def ensure_sales_skills():
    """Ensure monetization-focused sales skills per agent."""
    try:
        data = request.get_json(silent=True) or {}
        per_agent = int(data.get('per_agent', 50))
        result = agent_skillset.ensure_sales_skillsets_per_agent(count=per_agent)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/paypal/ensure', methods=['POST'])
def ensure_paypal_skills():
    """Ensure PayPal monetization skills per agent."""
    try:
        data = request.get_json(silent=True) or {}
        per_agent = int(data.get('per_agent', 15))
        result = agent_skillset.ensure_paypal_skillsets_per_agent(count=per_agent)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/top25/ensure', methods=['POST'])
def ensure_top25_skills():
    """Ensure top-25 new skills and upgrades per agent."""
    try:
        data = request.get_json(silent=True) or {}
        per_agent = int(data.get('per_agent', 25))
        result = agent_skillset.ensure_top25_skill_upgrades_per_agent(count=per_agent)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/shared-growth/ensure', methods=['POST'])
def ensure_shared_growth_skills():
    """Ensure shared growth skill pool across existing agents."""
    try:
        data = request.get_json(silent=True) or {}
        count = int(data.get('count', 100))
        result = agent_skillset.ensure_shared_growth_skills(count=count)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/blueprint-route-fixer/ensure', methods=['POST'])
def ensure_blueprint_route_fixer_skills_route():
    """Ensure blueprint & route fixer skills on every agent (Register Intelligence workflows)."""
    try:
        result = agent_skillset.ensure_blueprint_route_fixer_skills_per_agent()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/api-service/ensure', methods=['POST'])
def ensure_api_service_skills_route():
    """Ensure API service / REST contract awareness skills on every agent."""
    try:
        result = agent_skillset.ensure_api_service_skills_per_agent()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/progression/update', methods=['POST'])
def update_agent_progression():
    """Update all agent levels/experience from tracked results."""
    try:
        data = request.get_json(silent=True) or {}
        exp_mult = float(data.get('experience_multiplier', 10.0))
        success_weight = float(data.get('success_weight', 0.7))
        result = agent_skillset.update_agent_progression_from_results(
            experience_multiplier=exp_mult,
            success_weight=success_weight,
        )
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agents/skillsets/next-steps', methods=['GET'])
def get_agent_next_steps():
    """Get next-step recommendations generated from progression logic."""
    try:
        data = agent_skillset.get_all_skillsets()
        next_steps = data.get('agent_next_steps', {})
        return jsonify({'success': True, 'next_steps': next_steps}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@agent_automation_bp.route('/api/agent/skillset/search', methods=['GET'])
def search_agents_by_skill():
    """Search for agents with a specific skill"""
    try:
        skill = request.args.get('skill')
        if not skill:
            return jsonify({
                'success': False,
                'error': 'skill parameter required'
            }), 400
        
        results = agent_skillset.search_agents_by_skill(skill)
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== ABILITY TRACKER ENDPOINTS ==========

@agent_automation_bp.route('/api/agent/ability-tracker/stats', methods=['GET'])
def get_ability_tracker_stats():
    """Get all ability tracker statistics"""
    try:
        stats = agent_ability_tracker.get_all_stats()
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/agent/<agent_id>', methods=['GET'])
def get_agent_ability_stats(agent_id):
    """Get ability statistics for an agent"""
    try:
        stats = agent_ability_tracker.get_agent_stats(agent_id)
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/skill/<skill>', methods=['GET'])
def get_skill_ability_stats(skill):
    """Get ability statistics for a skill"""
    try:
        stats = agent_ability_tracker.get_skill_stats(skill)
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/track', methods=['POST'])
def track_skill_usage():
    """Track skill usage"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        skill = data.get('skill')
        success = data.get('success', True)
        metadata = data.get('metadata', {})
        
        if not agent_id or not skill:
            return jsonify({
                'success': False,
                'error': 'agent_id and skill required'
            }), 400
        
        agent_ability_tracker.track_skill_usage(agent_id, skill, success, metadata)
        return jsonify({
            'success': True,
            'message': f'Skill usage tracked for {agent_id}'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/activity', methods=['GET'])
def get_recent_activity():
    """Get recent activity"""
    try:
        limit = int(request.args.get('limit', 50))
        activity = agent_ability_tracker.get_recent_activity(limit)
        return jsonify({
            'success': True,
            'activity': activity,
            'count': len(activity)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@agent_automation_bp.route('/api/agents/activity/all', methods=['GET'])
def get_all_agents_activity():
    """Get unified recent activity for all agents."""
    try:
        limit = min(5000, max(10, int(request.args.get('limit', 1200))))
        activity = []

        # Source 1: ability tracker events
        try:
            tracker_activity = agent_ability_tracker.get_recent_activity(limit)
            for item in tracker_activity:
                activity.append({
                    'source': 'ability_tracker',
                    'timestamp': item.get('timestamp') or datetime.utcnow().isoformat(),
                    'agent_id': item.get('agent_id') or 'unknown',
                    'event': item.get('skill') or item.get('event') or 'skill_activity',
                    'status': 'success' if item.get('success', True) else 'failed',
                    'details': item,
                })
        except Exception:
            pass

        # Source 2: activation history
        try:
            from backend.services.agent_activation_system import agent_activation_system
            hist = (agent_activation_system.activations or {}).get('activation_history', [])
            for item in hist[-limit:]:
                activity.append({
                    'source': 'activation_system',
                    'timestamp': item.get('timestamp') or datetime.utcnow().isoformat(),
                    'agent_id': 'activation_system',
                    'event': item.get('function') or item.get('activation_name') or 'activation',
                    'status': 'success' if item.get('success', False) else 'failed',
                    'details': item,
                })
        except Exception:
            pass

        # Source 3: secretary activity log
        try:
            log_path = os.path.join(BASE_DIR, 'logs', 'agents', 'activity_log.json')
            if os.path.exists(log_path):
                with open(log_path, 'r', encoding='utf-8') as f:
                    payload = json.load(f)
                for item in (payload.get('activities', [])[-limit:]):
                    activity.append({
                        'source': 'secretary_log',
                        'timestamp': item.get('timestamp') or datetime.utcnow().isoformat(),
                        'agent_id': 'agent_secretary',
                        'event': item.get('type') or 'document_activity',
                        'status': 'logged',
                        'details': item.get('details', {}),
                    })
        except Exception:
            pass

        # Sort by timestamp desc
        activity = sorted(
            activity,
            key=lambda x: str(x.get('timestamp', '')),
            reverse=True,
        )[:limit]

        return jsonify({
            'success': True,
            'activity': activity,
            'count': len(activity),
            'sources': ['ability_tracker', 'activation_system', 'secretary_log'],
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/activity/agent/<agent_id>', methods=['GET'])
def get_agent_activity(agent_id):
    """Get recent activity for an agent"""
    try:
        limit = int(request.args.get('limit', 50))
        activity = agent_ability_tracker.get_agent_activity(agent_id, limit)
        return jsonify({
            'success': True,
            'activity': activity,
            'count': len(activity)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/activity/skill/<skill>', methods=['GET'])
def get_skill_activity(skill):
    """Get recent activity for a skill"""
    try:
        limit = int(request.args.get('limit', 50))
        activity = agent_ability_tracker.get_skill_activity(skill, limit)
        return jsonify({
            'success': True,
            'activity': activity,
            'count': len(activity)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/ability-tracker/reset/<agent_id>', methods=['POST'])
def reset_agent_stats(agent_id):
    """Reset statistics for an agent"""
    try:
        agent_ability_tracker.reset_agent_stats(agent_id)
        return jsonify({
            'success': True,
            'message': f'Statistics reset for {agent_id}'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ========== GROUPS ENDPOINTS ==========

@agent_automation_bp.route('/api/agent/groups', methods=['GET'])
def get_groups():
    """Get all groups"""
    try:
        groups = agent_groups.get_all_groups()
        return jsonify({
            'success': True,
            'groups': groups
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/groups/<group_id>', methods=['GET'])
def get_group(group_id):
    """Get a specific group"""
    try:
        group = agent_groups.get_group(group_id)
        stats = agent_groups.get_group_stats(group_id)
        return jsonify({
            'success': True,
            'group': group,
            'stats': stats
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_automation_bp.route('/api/agent/groups/<group_id>/add-member', methods=['POST'])
def add_member(group_id):
    """Add member to group"""
    try:
        data = request.get_json() or {}
        member_type = data.get('member_type')
        member = data.get('member')
        
        if not member_type or not member:
            return jsonify({
                'success': False,
                'error': 'member_type and member required'
            }), 400
        
        agent_groups.add_member(group_id, member_type, member)
        return jsonify({
            'success': True,
            'message': f'Member added to {group_id}'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ---------------------------------------------------------------------------
# AI-Powered Agent Intelligence Endpoints
# ---------------------------------------------------------------------------

@agent_automation_bp.route('/api/agent/automation/ai-strategy', methods=['GET', 'POST'])
def agent_ai_strategy():
    """
    DeepSeek R1-powered strategic automation plan.
    Analyses current agent state and recommends the next 5 automation actions.

    GET  ?user_id=X
    POST {"user_id": "X", "goal": "optional goal description"}
    """
    try:
        if request.method == 'POST':
            data = request.get_json(silent=True) or {}
        else:
            data = request.args.to_dict()

        user_id = data.get('user_id', 'default_user')
        goal    = data.get('goal', 'maximize XP and video generation efficiency')

        # Gather automation context
        ctx = {}
        try:
            ctx['automation_status'] = agent_automation.get_status()
        except Exception:
            pass
        try:
            ctx['skillsets'] = list((agent_skillset.get_all_skillsets().get('agents') or {}).keys())[:10]
        except Exception:
            pass
        try:
            ctx['groups'] = list((agent_groups.get_all_groups() or {}).keys())[:5]
        except Exception:
            pass

        from backend.services.llm_service import chat
        resp = chat(
            messages=[
                {
                    'role': 'system',
                    'content': (
                        'You are the AI strategy engine for MasterNoder.dk automated agents. '
                        'Analyse the current automation state and return a JSON action plan: '
                        '{"strategy_summary": str, "next_actions": [{"action": str, "why": str, '
                        '"api_endpoint": str, "priority": "high|medium|low"}], '
                        '"efficiency_score": int (0-100), "bottleneck": str}. '
                        'Respond ONLY with valid JSON.'
                    ),
                },
                {
                    'role': 'user',
                    'content': (
                        f'Goal: {goal}\n'
                        f'Automation state: {json.dumps(ctx, default=str)[:1500]}'
                    ),
                },
            ],
            task_type='reason',
            max_tokens=700,
            temperature=0.5,
        )

        plan = {}
        if resp.success:
            raw = resp.content.strip().lstrip('```json').lstrip('```').rstrip('```').strip()
            try:
                plan = json.loads(raw)
            except Exception:
                plan = {'strategy_summary': resp.content, 'next_actions': []}

        return jsonify({
            'success':  True,
            'user_id':  user_id,
            'goal':     goal,
            'plan':     plan,
            'provider': resp.provider if resp.success else None,
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@agent_automation_bp.route('/api/agent/automation/ai-diagnose', methods=['GET'])
def agent_ai_diagnose():
    """
    AI diagnosis of automation health — finds issues and suggests fixes.
    Uses Groq for fast analysis.
    """
    try:
        issues   = []
        warnings = []

        try:
            status = agent_automation.get_status()
            if not status.get('running'):
                issues.append('Automation is not running')
            if int(status.get('agents_active', 0)) == 0:
                warnings.append('No active agents found')
        except Exception as e:
            issues.append(f'Cannot read automation status: {e}')

        try:
            skillsets = agent_skillset.get_all_skillsets()
            agents = skillsets.get('agents') or {}
            low_level = [aid for aid, a in agents.items() if int(a.get('level', 1)) < 2]
            if len(low_level) > 5:
                warnings.append(f'{len(low_level)} agents at level 1 — consider upgrading')
        except Exception:
            pass

        # AI diagnosis
        diagnosis = ''
        recommendations = []
        try:
            from backend.services.llm_service import chat
            problem_desc = (
                f"Issues: {issues or 'none'}. Warnings: {warnings or 'none'}."
                if (issues or warnings) else "System appears healthy."
            )
            resp = chat(
                messages=[{'role': 'user', 'content':
                    f'Diagnose this MasterNoder.dk agent automation system: {problem_desc} '
                    'Give 3 specific recommendations in plain text, numbered 1-3.'}],
                task_type='speed',
                max_tokens=200,
                temperature=0.4,
            )
            if resp.success:
                diagnosis = resp.content.strip()
                lines = [l.strip() for l in diagnosis.split('\n') if l.strip()]
                recommendations = [l for l in lines if l[0].isdigit()][:3]
        except Exception:
            pass

        health_score = max(0, 100 - len(issues) * 30 - len(warnings) * 10)
        return jsonify({
            'success':         True,
            'health_score':    health_score,
            'status':          'healthy' if health_score >= 70 else 'degraded' if health_score >= 40 else 'critical',
            'issues':          issues,
            'warnings':        warnings,
            'diagnosis':       diagnosis,
            'recommendations': recommendations,
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _daemon_tick_auth_ok() -> bool:
    secret = (os.environ.get('AGENT_DAEMON_SECRET') or os.environ.get('AGENT_CRON_SECRET') or '').strip()
    if not secret:
        return False
    tok = (
        request.headers.get('X-Agent-Daemon-Token')
        or request.headers.get('X-Agent-Cron-Token')
        or request.args.get('token')
        or ''
    ).strip()
    return tok == secret


def _daemon_prod() -> bool:
    return (os.environ.get('FLASK_ENV') == 'production') or (
        str(os.environ.get('PRODUCTION', '')).lower() in ('1', 'true', 'yes')
    )


@agent_automation_bp.route('/api/agents/daemon/tick', methods=['POST'])
def agent_daemon_tick():
    """
    Called on an interval by scripts/agent_daemon.py (systemd).
    Runs agent_automation scheduled tasks once (blueprint/DB/missing-methods scans per config).
    Set AGENT_DAEMON_CONTROLS_AUTOMATION=1 on uwsgi to disable in-process automation threads.
    """
    secret = (os.environ.get('AGENT_DAEMON_SECRET') or os.environ.get('AGENT_CRON_SECRET') or '').strip()
    if not secret:
        if _daemon_prod():
            return jsonify({'success': False, 'error': 'Set AGENT_DAEMON_SECRET or AGENT_CRON_SECRET'}), 503
    elif not _daemon_tick_auth_ok():
        return jsonify({'success': False, 'error': 'unauthorized'}), 401

    try:
        agent_automation._execute_scheduled_tasks()
        agent_automation._run_maintenance_tasks()
        status = agent_automation.get_status()
        return jsonify({
            'success': True,
            'tick_at': datetime.utcnow().isoformat() + 'Z',
            'running': status.get('running'),
            'tasks_count': status.get('tasks_count'),
            'active_threads': status.get('active_threads'),
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
