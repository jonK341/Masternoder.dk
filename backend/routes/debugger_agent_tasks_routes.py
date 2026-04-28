"""
Debugger Agent Tasks Routes
Assign agents to work on tasks in each debugger tab and award points
"""
from flask import Blueprint, request, jsonify
from typing import Dict, List, Optional
from datetime import datetime
import os

debugger_agent_tasks_bp = Blueprint('debugger_agent_tasks', __name__)

# Initialize services with error handling
agent_manager = None
agent_point_creator = None

try:
    from backend.services.agent_manager import AgentManager
    agent_manager = AgentManager()
except (ImportError, Exception) as e:
    print(f"[WARN] Could not import AgentManager: {e}")
    agent_manager = None

try:
    from backend.services.agent_point_creator import AgentPointCreator
    agent_point_creator = AgentPointCreator()
except (ImportError, Exception) as e:
    print(f"[WARN] Could not import AgentPointCreator: {e}")
    agent_point_creator = None

# Points configuration for each tab - ENHANCED WITH MORE POINTS
TAB_POINTS = {
    'systems': {
        'debug_system': {'xp': 30, 'activity_points': 10},  # Doubled
        'debug_all_systems': {'xp': 100, 'activity_points': 40},  # Doubled
        'run_health_checker': {'xp': 35, 'activity_points': 14},
    },
    'routes': {
        'debug_route': {'xp': 20, 'activity_points': 6},  # Doubled
        'debug_all_routes': {'xp': 80, 'activity_points': 30}  # Doubled
    },
    'frontend': {
        'debug_frontend': {'xp': 24, 'activity_points': 8}  # Doubled
    },
    'url-test': {
        'test_url': {'xp': 10, 'activity_points': 4},  # Doubled
        'test_all_routes': {'xp': 60, 'activity_points': 24},  # Doubled
        'find_broken_urls': {'xp': 50, 'activity_points': 20}  # Doubled
    },
    'blueprints': {
        'check_duplicates': {'xp': 40, 'activity_points': 16}  # Doubled
    },
    'scanner': {
        'scan_all': {'xp': 60, 'activity_points': 24},  # Doubled
        'get_blueprints': {'xp': 20, 'activity_points': 8},  # Doubled
        'get_routes': {'xp': 20, 'activity_points': 8},  # Doubled
        'find_missing': {'xp': 50, 'activity_points': 20},  # Doubled
        'get_suggestions': {'xp': 30, 'activity_points': 12},  # Doubled
        'generate_methods': {'xp': 100, 'activity_points': 40}  # Doubled
    },
    'report': {
        'generate_report': {'xp': 70, 'activity_points': 30}  # Doubled
    },
    'errors': {
        'migrate_error_handler': {'xp': 50, 'activity_points': 20},  # New
        'complete_migration': {'xp': 100, 'activity_points': 40},  # New
        'analyze_errors': {'xp': 30, 'activity_points': 12}  # New
    },
    'master-dashboard': {
        'view_top10': {'xp': 10, 'activity_points': 5},  # New
        'refresh_stats': {'xp': 15, 'activity_points': 6}  # New
    },
    'ai-intelligence': {
        'view_top10': {'xp': 10, 'activity_points': 5},  # New
        'get_insights': {'xp': 20, 'activity_points': 8}  # New
    },
    'ops-4d': {
        'ops_refresh_4d_hub': {'xp': 28, 'activity_points': 11},
        'ops_agent_video_troubleshoot': {'xp': 45, 'activity_points': 18},
        'ops_verify_generator_jobs': {'xp': 32, 'activity_points': 13},
    },
}

# Free agents for rulebook / starmap25 todo assignments (round-robin)
FREE_AGENTS = ['content_generator_agent', 'learning_agent', 'analytics_agent', 'reporter_agent']

# Rulebook Todo 25 (from docs/RULEBOOK_TODO_25.md) — task_id, description, tab
RULEBOOK_TODO_TASKS = [
    {'task_id': 'rulebook_todo_%02d' % i, 'description': d, 'tab': 'rulebook'}
    for i, d in enumerate([
        'V1 Core — compendium + data + API', 'V2 Hunters — 19 spells, 5 sectors', 'V3 Comm. Psychology — 25 theories',
        'V3.2 Systemic Protocols — 13 protocols', 'V4 Star Map — 7 stars, verification', 'V5 Effect Clusters',
        'V6 Electric Magnet — specials, tech tree', 'V7 Unified Points — add_points, triggers', 'V8 Agents & Skillsets',
        'V9 Shop — items, purchases', 'V10 Battle — profiling, geo_ref', 'V11 DNA — run_dna_test',
        'V12 Generator — content categories', 'V13 Geo & Session', 'V14 Analytics — event tracker',
        'V15 Index — catalog in sync', 'API GET /api/rulebooks/index', 'API GET /api/rulebooks/<version>',
        'API GET /api/rulebooks/agent-context', 'Agent schema in all rulebooks', 'Data files — each version has JSON',
        'Compendium UI — page lists rulebooks', 'Agent knowledge API', 'Docs sync compendium ↔ data', 'Deploy rulebook routes',
    ], 1)
]

# Star Map 25 Todo (from docs/STARMAP25_TODO_25.md) — first 10 for assignment
STARMAP25_TODO_TASKS = [
    {'task_id': 'starmap25_todo_%02d' % i, 'description': d, 'tab': 'starmap25'}
    for i, d in enumerate([
        'Data star_map_25.json — 25 points', 'API GET /api/star-map/25', 'API GET /api/star-map/25/status',
        'API POST /api/star-map/25/investigate', 'Persistence — investigations survive restart',
        'Monitor page /vidgenerator/starmap25/', 'Grid of 25 cards + Investigate', 'View toggles Grid/3D',
        'Live indicator + 30s refresh', 'Navigation — Star Map 25 link',
    ], 1)
]


def _load_starmap50_projects() -> List[Dict]:
    """Load Star Map 25 — 50 projects from data/starmap25_agent_projects.json (AIs + agents)."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(base_dir, "data", "starmap25_agent_projects.json")
    if os.path.exists(path):
        try:
            import json
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            projects = data.get("projects") or []
            agents = data.get("agents") or FREE_AGENTS
            return [
                {
                    "task_id": p.get("task_id", "starmap50_%02d" % p.get("num", i + 1)),
                    "description": p.get("description", ""),
                    "tab": "starmap25",
                    "suggested_agent": p.get("suggested_agent") or agents[idx % len(agents)],
                }
                for idx, p in enumerate(projects)
            ]
        except Exception as e:
            print(f"[WARN] Could not load starmap25_agent_projects.json: {e}")
    return []


@debugger_agent_tasks_bp.route('/api/debugger/tasks/generate', methods=['POST'])
def generate_debugger_tasks():
    """Generate tasks for all debugger tabs"""
    try:
        tasks = []
        
        # Systems tab tasks
        tasks.append({
            'task_id': 'systems_debug_all',
            'tab': 'systems',
            'action': 'debug_all_systems',
            'description': 'Debug all systems and identify issues',
            'points_reward': TAB_POINTS['systems']['debug_all_systems'],
            'priority': 'high'
        })
        
        # Routes tab tasks
        tasks.append({
            'task_id': 'routes_debug_all',
            'tab': 'routes',
            'action': 'debug_all_routes',
            'description': 'Debug all routes and check for errors',
            'points_reward': TAB_POINTS['routes']['debug_all_routes'],
            'priority': 'high'
        })
        
        # Frontend tab tasks
        tasks.append({
            'task_id': 'frontend_scan',
            'tab': 'frontend',
            'action': 'debug_frontend',
            'description': 'Scan frontend files for issues',
            'points_reward': TAB_POINTS['frontend']['debug_frontend'],
            'priority': 'medium'
        })
        
        # URL Test tab tasks
        tasks.append({
            'task_id': 'url_find_broken',
            'tab': 'url-test',
            'action': 'find_broken_urls',
            'description': 'Find and report all broken URLs',
            'points_reward': TAB_POINTS['url-test']['find_broken_urls'],
            'priority': 'high'
        })
        
        # Blueprints tab tasks
        tasks.append({
            'task_id': 'blueprints_check_duplicates',
            'tab': 'blueprints',
            'action': 'check_duplicates',
            'description': 'Check for duplicate blueprints',
            'points_reward': TAB_POINTS['blueprints']['check_duplicates'],
            'priority': 'medium'
        })
        
        # Scanner tab tasks
        tasks.append({
            'task_id': 'scanner_scan_all',
            'tab': 'scanner',
            'action': 'scan_all',
            'description': 'Scan entire codebase for API issues',
            'points_reward': TAB_POINTS['scanner']['scan_all'],
            'priority': 'high'
        })
        
        tasks.append({
            'task_id': 'scanner_find_missing',
            'tab': 'scanner',
            'action': 'find_missing',
            'description': 'Find missing API methods',
            'points_reward': TAB_POINTS['scanner']['find_missing'],
            'priority': 'high'
        })
        
        # Report tab tasks
        tasks.append({
            'task_id': 'report_generate',
            'tab': 'report',
            'action': 'generate_report',
            'description': 'Generate comprehensive debug report',
            'points_reward': TAB_POINTS['report']['generate_report'],
            'priority': 'medium'
        })

        # 4D Monitor & Ops hub — user process, video pipeline, agent troubleshooters
        tasks.append({
            'task_id': 'ops_4d_refresh_hub',
            'tab': 'ops-4d',
            'action': 'ops_refresh_4d_hub',
            'description': 'Refresh 4D monitor (user process, health, agent stats, timeline)',
            'points_reward': TAB_POINTS['ops-4d']['ops_refresh_4d_hub'],
            'priority': 'medium',
        })
        tasks.append({
            'task_id': 'ops_4d_video_troubleshoot',
            'tab': 'ops-4d',
            'action': 'ops_agent_video_troubleshoot',
            'description': 'Run AI video / pipeline troubleshoot (solve-problems) from hub notes',
            'points_reward': TAB_POINTS['ops-4d']['ops_agent_video_troubleshoot'],
            'priority': 'high',
        })
        tasks.append({
            'task_id': 'ops_4d_verify_jobs',
            'tab': 'ops-4d',
            'action': 'ops_verify_generator_jobs',
            'description': 'Verify generator jobs list and documentary progress for active user',
            'points_reward': TAB_POINTS['ops-4d']['ops_verify_generator_jobs'],
            'priority': 'medium',
        })

        tasks.append({
            'task_id': 'systems_run_health_checker',
            'tab': 'systems',
            'action': 'run_health_checker',
            'description': 'Run /api/health checker grid and award debugger points',
            'points_reward': TAB_POINTS['systems']['run_health_checker'],
            'priority': 'high',
        })
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'total_tasks': len(tasks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/assign', methods=['POST'])
def assign_debugger_task():
    """Assign a debugger task to an agent"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        agent_id = data.get('agent_id', 'agent_manager')
        tab = data.get('tab')
        action = data.get('action')
        target_user_id = (data.get('user_id') or request.args.get('user_id') or '').strip() or 'system'

        if not task_id or not tab or not action:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: task_id, tab, action'
            }), 400
        
        # Get points for this action
        points = TAB_POINTS.get(tab, {}).get(action, {'xp': 10, 'activity_points': 5})
        
        # Award points for accepting task
        point_result = None
        if agent_point_creator:
            try:
                point_result = agent_point_creator.award_points_for_agent_action(
                    agent_id=agent_id,
                    action='accept_debugger_task',
                    user_id=target_user_id,
                    points={'xp': 5, 'activity_points': 2}
                )
            except Exception as e:
                print(f"[WARN] Could not award points: {e}")
                point_result = {'points_awarded': {'xp': 5, 'activity_points': 2}}
        else:
            point_result = {'points_awarded': {'xp': 5, 'activity_points': 2}}
        
        # Assign task via agent manager
        assignment_result = None
        if agent_manager:
            try:
                assignment_result = agent_manager.assign_task(
                    agent_id=agent_id,
                    task_id=task_id,
                    task_data={
                        'tab': tab,
                        'action': action,
                        'points_reward': points,
                        'status': 'assigned'
                    }
                )
            except Exception as e:
                print(f"[WARN] Could not assign task via agent manager: {e}")
                assignment_result = {'success': True, 'status': 'assigned'}
        else:
            assignment_result = {'success': True, 'status': 'assigned'}
        
        # Save task assignment to database
        ai_assignment = None
        try:
            from backend.utils.agent_task_database import save_agent_task
            
            # Get task description from generated tasks
            description = f"{tab} - {action}"
            try:
                tasks_response = generate_debugger_tasks()
                if hasattr(tasks_response, 'get_json'):
                    tasks_data = tasks_response.get_json()
                else:
                    tasks_data = tasks_response if isinstance(tasks_response, dict) else {}
                
                for task in tasks_data.get('tasks', []):
                    if task.get('task_id') == task_id:
                        description = task.get('description', description)
                        break
            except:
                pass
            
            save_agent_task({
                'task_id': task_id,
                'agent_id': agent_id,
                'task_type': 'debugger_task',
                'tab': tab,
                'action': action,
                'description': description,
                'status': 'assigned',
                'priority': 'medium',
                'points_reward': points,
                'assigned_at': datetime.utcnow().isoformat()
            })
            
            # Try to get AI-enhanced assignment if available
            try:
                from backend.services.ai_enhanced_agent_tasks import ai_enhanced_agent_tasks
                if ai_enhanced_agent_tasks:
                    ai_assignment = ai_enhanced_agent_tasks.enhance_task_assignment(
                        task_data={
                            'task_id': task_id,
                            'tab': tab,
                            'action': action,
                            'description': description
                        },
                        agent_id=agent_id
                    )
            except Exception as e:
                print(f"[WARN] Could not get AI assignment: {e}")
        except Exception as e:
            print(f"[WARN] Could not save task assignment to database: {e}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'agent_id': agent_id,
            'points': point_result.get('points_awarded', {}) if point_result else {},
            'assignment': assignment_result,
            'ai_assignment': ai_assignment
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/complete', methods=['POST'])
def complete_debugger_task():
    """Mark a debugger task as complete and award points"""
    try:
        data = request.get_json() or {}
        task_id = data.get('task_id')
        agent_id = data.get('agent_id', 'agent_manager')
        tab = data.get('tab')
        action = data.get('action')
        result_data = data.get('result_data', {})
        target_user_id = (data.get('user_id') or request.args.get('user_id') or '').strip() or 'system'

        if not task_id or not tab or not action:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: task_id, tab, action'
            }), 400
        
        # Get points for this action
        points = TAB_POINTS.get(tab, {}).get(action, {'xp': 10, 'activity_points': 5})
        
        # Award points for completing task with fallback
        if agent_point_creator:
            try:
                point_result = agent_point_creator.award_points_for_agent_action(
                    agent_id=agent_id,
                    action='complete_debugger_task',
                    user_id=target_user_id,
                    points=points
                )
            except Exception as e:
                print(f"[WARN] Could not award points: {e}")
                point_result = {'points_awarded': points}
        else:
            point_result = {'points_awarded': points}
        
        # Save task completion to database
        achievements_unlocked = []
        try:
            from backend.utils.agent_task_database import save_agent_task, mark_task_completed
            
            # First try to mark as completed
            if not mark_task_completed(task_id, point_result.get('points_awarded', points), result_data):
                # If task doesn't exist, create it
                save_agent_task({
                    'task_id': task_id,
                    'agent_id': agent_id,
                    'task_type': 'debugger_task',
                    'tab': tab,
                    'action': action,
                    'description': f"{tab} - {action}",
                    'status': 'completed',
                    'priority': 'medium',
                    'points_reward': points,
                    'points_awarded': point_result.get('points_awarded', points),
                    'result_data': result_data,
                    'completed_at': datetime.utcnow().isoformat()
                })
            
            # Check for achievements
            try:
                from backend.services.agent_achievements import agent_achievements
                achievements_unlocked = agent_achievements.check_achievements(
                    agent_id=agent_id,
                    action='task_completed',
                    data={
                        'xp': points.get('xp', 0),
                        'activity_points': points.get('activity_points', 0),
                        'tab': tab
                    }
                )
                # Also check tab-specific achievement
                if achievements_unlocked:
                    agent_achievements.check_achievements(
                        agent_id=agent_id,
                        action='tab_task_completed',
                        data={'tab': tab}
                    )
            except Exception as e:
                print(f"[WARN] Could not check achievements: {e}")
            
            # Learn from task and update intelligence with AI
            try:
                from backend.services.agent_ai_intelligence import agent_ai_intelligence, TECH_SECTORS
                from backend.services.agent_reengineering import agent_reengineering
                from backend.services.ai_enhanced_agent_tasks import ai_enhanced_agent_tasks
                
                # Determine tech sector from tab/action
                sector = 'backend'  # Default
                if 'frontend' in tab.lower():
                    sector = 'frontend'
                elif 'database' in tab.lower() or 'blueprint' in tab.lower():
                    sector = 'database'
                elif 'route' in tab.lower() or 'api' in action.lower():
                    sector = 'backend'
                
                # Update tech sector intelligence
                agent_ai_intelligence.update_tech_sector_intelligence(
                    sector=sector,
                    task_result={
                        'success': True,
                        'task_type': 'debugger_task',
                        'action': action,
                        'tab': tab
                    }
                )
                
                # Learn from task for reengineering
                agent_reengineering.learn_from_task(
                    task_data={
                        'task_type': 'debugger_task',
                        'action': action,
                        'tab': tab
                    },
                    result_data=result_data
                )
                
                # Use AI to optimize future task execution
                try:
                    session_data = {
                        'actions_count': 1,
                        'errors_count': 0
                    }
                    optimization = ai_enhanced_agent_tasks.optimize_task_execution(
                        task_data={
                            'task_type': 'debugger_task',
                            'action': action,
                            'tab': tab
                        },
                        session_data=session_data
                    )
                    # Store optimization insights
                    result_data['ai_optimization'] = optimization
                except Exception as e:
                    print(f"[WARN] Could not optimize with AI: {e}")
            except Exception as e:
                print(f"[WARN] Could not update intelligence: {e}")
        except Exception as e:
            print(f"[WARN] Could not save task to database: {e}")
        
        return jsonify({
            'success': True,
            'task_id': task_id,
            'agent_id': agent_id,
            'points_awarded': point_result.get('points_awarded', {}),
            'result_data': result_data,
            'task_marked_completed': True,
            'achievements_unlocked': achievements_unlocked
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/list', methods=['GET'])
def list_debugger_tasks():
    """List all available debugger tasks"""
    try:
        tab = request.args.get('tab')
        include_completed = request.args.get('include_completed', 'false').lower() == 'true'
        
        # Generate all tasks
        response = generate_debugger_tasks()
        tasks_data = response.get_json()
        
        if not tasks_data.get('success'):
            return jsonify(tasks_data), 500
        
        tasks = tasks_data.get('tasks', [])
        
        # Filter by tab if specified
        if tab:
            tasks = [t for t in tasks if t.get('tab') == tab]
        
        # Get completion status from database
        try:
            from backend.utils.agent_task_database import get_agent_tasks
            
            db_tasks = get_agent_tasks(tab=tab if tab else None)
            task_status_map = {t['task_id']: t['status'] for t in db_tasks}
            
            # Add completion status to tasks
            for task in tasks:
                task_id = task.get('task_id')
                if task_id in task_status_map:
                    task['status'] = task_status_map[task_id]
                    task['completed'] = task_status_map[task_id] == 'completed'
                else:
                    task['status'] = 'pending'
                    task['completed'] = False
            
            # Filter out completed tasks if not requested
            if not include_completed:
                tasks = [t for t in tasks if not t.get('completed', False)]
        except Exception as e:
            print(f"[WARN] Could not get task status from database: {e}")
            for task in tasks:
                task['status'] = 'pending'
                task['completed'] = False
        
        return jsonify({
            'success': True,
            'tasks': tasks,
            'total_tasks': len(tasks)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/stats', methods=['GET'])
def get_debugger_task_stats():
    """Get statistics about debugger tasks"""
    try:
        response = generate_debugger_tasks()
        tasks_data = response.get_json()
        
        if not tasks_data.get('success'):
            return jsonify(tasks_data), 500
        
        tasks = tasks_data.get('tasks', [])
        
        # Calculate stats
        total_xp = sum(t.get('points_reward', {}).get('xp', 0) for t in tasks)
        total_activity = sum(t.get('points_reward', {}).get('activity_points', 0) for t in tasks)
        
        tabs = {}
        for task in tasks:
            tab = task.get('tab')
            if tab not in tabs:
                tabs[tab] = {'count': 0, 'xp': 0, 'activity': 0}
            tabs[tab]['count'] += 1
            tabs[tab]['xp'] += task.get('points_reward', {}).get('xp', 0)
            tabs[tab]['activity'] += task.get('points_reward', {}).get('activity_points', 0)
        
        stats = {
            'total_tasks': len(tasks),
            'total_potential_xp': total_xp,
            'total_potential_activity': total_activity,
            'tabs': tabs,
        }
        return jsonify({
            'success': True,
            'total_tasks': len(tasks),
            'total_potential_xp': total_xp,
            'total_potential_activity': total_activity,
            'tabs': tabs,
            'stats': stats,
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/generate-rulebook-todo', methods=['POST'])
def generate_rulebook_todo():
    """Generate task list for Rulebook Todo 25 and Star Map 25 Todo. Returns tasks only (no assign)."""
    try:
        tasks = []
        for t in RULEBOOK_TODO_TASKS:
            tasks.append({
                'task_id': t['task_id'],
                'tab': t['tab'],
                'action': 'verify_rulebook',
                'description': t['description'],
                'points_reward': {'xp': 15, 'activity_points': 6},
                'priority': 'medium',
            })
        for t in STARMAP25_TODO_TASKS:
            tasks.append({
                'task_id': t['task_id'],
                'tab': t['tab'],
                'action': 'verify_starmap25',
                'description': t['description'],
                'points_reward': {'xp': 12, 'activity_points': 5},
                'priority': 'medium',
            })
        return jsonify({'success': True, 'tasks': tasks, 'total': len(tasks)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/assign-rulebook-todo', methods=['POST'])
def assign_rulebook_todo():
    """Assign Rulebook Todo 25 and Star Map 25 Todo to free agents (round-robin) and save to agent_tasks.
    Use max_tasks=25 (or daily=true) to assign exactly 25 new assignments per run (e.g. daily job).
    Use only_starmap25=true and use_starmap50=true (or max_tasks=50) to assign all 50 Star Map projects to suggested agents."""
    try:
        data = request.get_json() or {}
        agents = data.get('agent_ids') or FREE_AGENTS
        only_rulebook = data.get('only_rulebook', False)
        only_starmap25 = data.get('only_starmap25', False)
        use_starmap50 = data.get('use_starmap50', False)
        max_tasks = data.get('max_tasks')
        if max_tasks is None and data.get('daily') and not use_starmap50:
            max_tasks = 25
        if max_tasks is not None:
            max_tasks = max(1, min(100, int(max_tasks)))

        all_tasks = []
        use_50_projects = only_starmap25 and (use_starmap50 or (max_tasks == 50))
        if use_50_projects:
            starmap50 = _load_starmap50_projects()
            for t in starmap50:
                all_tasks.append({
                    'task_id': t['task_id'],
                    'description': t['description'],
                    'tab': 'starmap25',
                    'suggested_agent': t.get('suggested_agent'),
                })
            if max_tasks is not None:
                all_tasks = all_tasks[:max_tasks]
        else:
            if not only_starmap25:
                all_tasks.extend(RULEBOOK_TODO_TASKS)
            if not only_rulebook:
                all_tasks.extend(STARMAP25_TODO_TASKS)
            if max_tasks is not None:
                all_tasks = all_tasks[:max_tasks]

        assigned = []
        for idx, t in enumerate(all_tasks):
            agent_id = t.get('suggested_agent') or agents[idx % len(agents)]
            task_id = t['task_id']
            tab = t.get('tab', 'starmap25')
            action = 'verify_rulebook' if tab == 'rulebook' else 'verify_starmap25'
            points = {'xp': 15, 'activity_points': 6} if tab == 'rulebook' else {'xp': 12, 'activity_points': 5}

            try:
                from backend.utils.agent_task_database import save_agent_task
                save_agent_task({
                    'task_id': task_id,
                    'agent_id': agent_id,
                    'task_type': 'rulebook_todo' if tab == 'rulebook' else 'starmap25_todo',
                    'tab': tab,
                    'action': action,
                    'description': t['description'],
                    'status': 'assigned',
                    'priority': 'medium',
                    'points_reward': points,
                    'assigned_at': datetime.utcnow().isoformat(),
                })
                assigned.append({'task_id': task_id, 'agent_id': agent_id, 'description': (t.get('description') or '')[:50]})
            except Exception as e:
                assigned.append({'task_id': task_id, 'agent_id': agent_id, 'error': str(e)})

        return jsonify({
            'success': True,
            'assigned': assigned,
            'total_assigned': len(assigned),
            'agents_used': agents,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@debugger_agent_tasks_bp.route('/api/debugger/tasks/assign-starmap50', methods=['POST'])
def assign_starmap50():
    """Assign all 50 Star Map 25 projects to AIs + agents (content_generator_agent, learning_agent, analytics_agent).
    Each project is assigned to its suggested_agent from data/starmap25_agent_projects.json."""
    try:
        projects = _load_starmap50_projects()
        if not projects:
            return jsonify({'success': False, 'error': 'No starmap50 projects loaded (check data/starmap25_agent_projects.json)'}), 400

        assigned = []
        for t in projects:
            agent_id = t.get('suggested_agent') or FREE_AGENTS[0]
            task_id = t['task_id']
            try:
                from backend.utils.agent_task_database import save_agent_task
                save_agent_task({
                    'task_id': task_id,
                    'agent_id': agent_id,
                    'task_type': 'starmap25_todo',
                    'tab': 'starmap25',
                    'action': 'verify_starmap25',
                    'description': t['description'],
                    'status': 'assigned',
                    'priority': 'medium',
                    'points_reward': {'xp': 12, 'activity_points': 5},
                    'assigned_at': datetime.utcnow().isoformat(),
                })
                assigned.append({'task_id': task_id, 'agent_id': agent_id, 'description': (t['description'] or '')[:50]})
            except Exception as e:
                assigned.append({'task_id': task_id, 'agent_id': agent_id, 'error': str(e)})

        agents_used = list({a['agent_id'] for a in assigned})
        return jsonify({
            'success': True,
            'assigned': assigned,
            'total_assigned': len(assigned),
            'agents_used': agents_used,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
