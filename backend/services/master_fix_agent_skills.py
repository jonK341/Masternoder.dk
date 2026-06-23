"""
Master Fix Agent Skills
Comprehensive agent skill system for automated maintenance and monitoring
"""
import os
import sys
import json
import re
import glob
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class MasterFixAgentSkills:
    """Agent skills for master fix operations"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.skills_dir = os.path.join(self.base_dir, 'logs', 'agent_skills')
        os.makedirs(self.skills_dir, exist_ok=True)
        self.history_file = os.path.join(self.skills_dir, 'skill_history.json')
        self.missions_file = os.path.join(self.skills_dir, 'missions.json')
        self.quests_file = os.path.join(self.skills_dir, 'quests.json')
        self.personality_file = os.path.join(self.skills_dir, 'agent_personality.json')
        self.load_data()
    
    def load_data(self):
        """Load agent data"""
        self.history = self._load_json(self.history_file, [])
        self.missions = self._load_json(self.missions_file, [])
        self.quests = self._load_json(self.quests_file, [])
        self.personality = self._load_json(self.personality_file, self._default_personality())
    
    def _load_json(self, filepath: str, default: Any):
        """Load JSON file with default"""
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return default
        return default
    
    def _save_json(self, filepath: str, data: Any):
        """Save JSON file"""
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving {filepath}: {e}")
    
    def _default_personality(self) -> Dict:
        """Default agent personality"""
        return {
            'name': 'Master Fix Agent',
            'personality_type': 'analytical',
            'traits': ['methodical', 'thorough', 'detail-oriented', 'proactive'],
            'behavior_patterns': {
                'scanning': 'comprehensive',
                'reporting': 'detailed',
                'fixing': 'cautious',
                'monitoring': 'continuous'
            },
            'preferences': {
                'detail_level': 'high',
                'report_frequency': 'regular',
                'auto_fix': False
            },
            'experience_level': 0,
            'skills_unlocked': [],
            'achievements': []
        }
    
    # ========== CORE SKILLS ==========
    
    def skill_check_blueprints(self) -> Dict:
        """Skill: Check blueprint registration"""
        try:
            from backend.services.api_scanner import APIScanner
            scanner = APIScanner(self.base_dir)
            blueprints = scanner.scan_blueprints()
            
            # Check registration against the already-running app (cheap). Building a
            # throwaway Flask app and re-importing every blueprint here costs ~50s, so
            # only fall back to that when no application context is available.
            # Inspect the already-running app only. Building a throwaway Flask
            # app + re-importing every blueprint here costs ~50s per call (and
            # this skill runs multiple times per diagnostic), which previously
            # blew past the uWSGI worker timeout in production. If there is no
            # application context we simply report registration as unknown.
            registered = []
            registration_source = 'current_app'
            try:
                from flask import current_app
                registered = list(current_app.blueprints.keys())
            except Exception:
                registered = []
                registration_source = 'unavailable'
            
            if registration_source == 'unavailable':
                # No app context: we can't reliably tell what's registered.
                unregistered = []
            else:
                unregistered = [bp for bp in blueprints if bp.get('name') not in registered]
            
            self._record_skill_use('check_blueprints', {
                'total': len(blueprints),
                'registered': len(registered),
                'unregistered': len(unregistered)
            })
            
            return {
                'success': True,
                'total_blueprints': len(blueprints),
                'registered': len(registered),
                'unregistered': len(unregistered),
                'unregistered_list': [bp['name'] for bp in unregistered],
                'registration_source': registration_source
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_verify_database(self) -> Dict:
        """Skill: Verify database tables"""
        try:
            import sqlite3
            db_path = os.path.join(self.base_dir, 'vidgenerator', 'instance', 'database.db')
            if not os.path.exists(db_path):
                db_path = os.path.join(self.base_dir, 'instance', 'database.db')
            
            if not os.path.exists(db_path):
                return {'success': False, 'error': 'Database not found'}
            
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Check required tables
            required_tables = ['player_levels', 'xp_history', 'daily_activities', 'rewards', 'user_rewards']
            existing_tables = []
            missing_tables = []
            
            for table in required_tables:
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    existing_tables.append(table)
                else:
                    missing_tables.append(table)
            
            conn.close()
            
            self._record_skill_use('verify_database', {
                'existing': len(existing_tables),
                'missing': len(missing_tables)
            })
            
            return {
                'success': True,
                'existing_tables': existing_tables,
                'missing_tables': missing_tables,
                'all_present': len(missing_tables) == 0
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_check_file_integrity(self) -> Dict:
        """Skill: Check file integrity"""
        try:
            critical_files = [
                'backend/register_blueprints.py',
                'backend/routes/hunters_game.py',
                'backend/services/api_scanner.py',
                'backend/services/api_monitoring_agent.py',
                'scripts/fix_all_loose_ends_master.py'
            ]
            
            results = {}
            for file_path in critical_files:
                full_path = os.path.join(self.base_dir, file_path)
                exists = os.path.exists(full_path)
                size = os.path.getsize(full_path) if exists else 0
                results[file_path] = {
                    'exists': exists,
                    'size': size,
                    'status': 'ok' if exists and size > 0 else 'missing'
                }
            
            missing = [f for f, r in results.items() if not r['exists']]
            
            self._record_skill_use('check_file_integrity', {
                'checked': len(critical_files),
                'missing': len(missing)
            })
            
            return {
                'success': True,
                'files_checked': len(critical_files),
                'files_ok': len(critical_files) - len(missing),
                'files_missing': len(missing),
                'results': results
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_check_navigation(self) -> Dict:
        """Skill: Check navigation links"""
        try:
            # Collect up to 50 HTML files using a pruned walk. A plain
            # rglob('*.html') enumerates the ENTIRE tree first (node_modules,
            # .git, venv, media uploads, ...) which can take >2min on the
            # production box, so prune heavy dirs and stop early instead.
            skip_dirs = {
                'node_modules', '.git', 'venv', 'env', '.venv', '__pycache__',
                'site-packages', 'dist', 'build', '.cache', '.next', 'coverage',
                'uploads', 'media', 'static_videos', 'generated_videos', 'tmp',
            }
            html_files = []
            for root, dirs, files in os.walk(self.base_dir):
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]
                for name in files:
                    if name.endswith('.html'):
                        html_files.append(os.path.join(root, name))
                        if len(html_files) >= 50:
                            break
                if len(html_files) >= 50:
                    break

            points_links = 0
            missing_links = []

            for html_file in html_files:
                try:
                    with open(html_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        if '/vidgenerator/points' in content or 'points/index.html' in content:
                            points_links += 1
                        elif 'navigation' in content.lower():
                            missing_links.append(os.path.relpath(html_file, self.base_dir))
                except:
                    pass
            
            self._record_skill_use('check_navigation', {
                'with_links': points_links,
                'missing_links': len(missing_links)
            })
            
            return {
                'success': True,
                'files_with_points_link': points_links,
                'files_missing_link': len(missing_links),
                'sample_missing': missing_links[:10]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_scan_missing_methods(self) -> Dict:
        """Skill: Scan for missing API methods"""
        try:
            from backend.services.api_scanner import APIScanner
            scanner = APIScanner(self.base_dir)
            missing = scanner.find_missing_methods()
            
            self._record_skill_use('scan_missing_methods', {
                'missing_count': len(missing)
            })
            
            return {
                'success': True,
                'missing_methods': len(missing),
                'methods': missing[:20]  # First 20
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_check_service_health(self) -> Dict:
        """Skill: Check service health"""
        try:
            import ast
            services_dir = os.path.join(self.base_dir, 'backend', 'services')
            services = []
            errors = []
            
            if os.path.exists(services_dir):
                for file in glob.glob(os.path.join(services_dir, '**/*.py'), recursive=True):
                    if '__pycache__' in file:
                        continue
                    rel_path = os.path.relpath(file, self.base_dir)
                    try:
                        # Verify the file parses WITHOUT executing it. Importing
                        # every service module here would run module-level code
                        # (DB/network/model init) and could hang for minutes in
                        # production, so we only check syntax validity.
                        with open(file, 'r', encoding='utf-8') as f:
                            ast.parse(f.read(), filename=rel_path)
                        services.append({
                            'file': rel_path,
                            'status': 'ok'
                        })
                    except Exception as e:
                        errors.append({
                            'file': rel_path,
                            'error': str(e)[:100]
                        })
            
            self._record_skill_use('check_service_health', {
                'healthy': len(services),
                'errors': len(errors)
            })
            
            return {
                'success': True,
                'healthy_services': len(services),
                'error_services': len(errors),
                'services': services[:10],
                'errors': errors[:10]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_analyze_code_quality(self) -> Dict:
        """Skill: Analyze code quality"""
        try:
            routes_dir = os.path.join(self.base_dir, 'backend', 'routes')
            issues = []
            stats = {
                'total_files': 0,
                'files_with_errors': 0,
                'files_with_warnings': 0
            }
            
            if os.path.exists(routes_dir):
                for file in glob.glob(os.path.join(routes_dir, '*.py')):
                    if file.endswith('.backup'):
                        continue
                    stats['total_files'] += 1
                    try:
                        with open(file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                            # Check for common issues
                            if 'except:' in content or 'except Exception:' in content:
                                if 'pass' in content.split('except')[1].split('\n')[0]:
                                    issues.append({
                                        'file': os.path.basename(file),
                                        'type': 'warning',
                                        'issue': 'Bare except with pass'
                                    })
                                    stats['files_with_warnings'] += 1
                    except:
                        stats['files_with_errors'] += 1
            
            self._record_skill_use('analyze_code_quality', stats)
            
            return {
                'success': True,
                'stats': stats,
                'issues': issues[:20]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_check_dependencies(self) -> Dict:
        """Skill: Check dependencies"""
        try:
            requirements_file = os.path.join(self.base_dir, 'requirements.txt')
            installed = []
            missing = []
            
            if os.path.exists(requirements_file):
                with open(requirements_file, 'r') as f:
                    requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                
                for req in requirements[:20]:  # Check first 20
                    package = req.split('==')[0].split('>=')[0].split('<=')[0]
                    try:
                        __import__(package.replace('-', '_'))
                        installed.append(package)
                    except:
                        missing.append(package)
            
            self._record_skill_use('check_dependencies', {
                'installed': len(installed),
                'missing': len(missing)
            })
            
            return {
                'success': True,
                'installed': len(installed),
                'missing': len(missing),
                'missing_list': missing
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_verify_endpoints(self) -> Dict:
        """Skill: Verify API endpoints"""
        try:
            from flask import Flask
            from backend.register_blueprints import register_all_blueprints
            
            app = Flask(__name__)
            app.config['TESTING'] = True
            register_all_blueprints(app)
            
            routes = []
            for rule in app.url_map.iter_rules():
                routes.append({
                    'rule': rule.rule,
                    'methods': list(rule.methods),
                    'endpoint': rule.endpoint
                })
            
            self._record_skill_use('verify_endpoints', {
                'total_routes': len(routes)
            })
            
            return {
                'success': True,
                'total_routes': len(routes),
                'routes': routes[:20]
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_monitor_api_structure(self) -> Dict:
        """Skill: Monitor API structure"""
        try:
            from backend.services.api_scanner import APIScanner
            scanner = APIScanner(self.base_dir)
            report = scanner.get_report()
            
            self._record_skill_use('monitor_api_structure', report['summary'])
            
            return {
                'success': True,
                'report': report['summary']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== MONITORING SKILLS ==========
    
    def skill_monitor_system_health(self) -> Dict:
        """Skill: Monitor overall system health"""
        try:
            health_score = 100
            issues = []
            
            # Check database
            db_check = self.skill_verify_database()
            if not db_check.get('all_present', False):
                health_score -= 20
                issues.append('Missing database tables')
            
            # Check blueprints
            bp_check = self.skill_check_blueprints()
            if bp_check.get('unregistered', 0) > 0:
                health_score -= 10
                issues.append(f"{bp_check['unregistered']} unregistered blueprints")
            
            # Check file integrity
            file_check = self.skill_check_file_integrity()
            if file_check.get('files_missing', 0) > 0:
                health_score -= 15
                issues.append(f"{file_check['files_missing']} missing files")
            
            # Check missing methods
            methods_check = self.skill_scan_missing_methods()
            missing_count = methods_check.get('missing_methods', 0)
            if missing_count > 50:
                health_score -= 10
                issues.append(f"{missing_count} missing methods")
            
            health_score = max(0, health_score)
            
            self._record_skill_use('monitor_system_health', {
                'health_score': health_score,
                'issues_count': len(issues)
            })
            
            return {
                'success': True,
                'health_score': health_score,
                'health_status': 'excellent' if health_score >= 90 else 'good' if health_score >= 70 else 'fair' if health_score >= 50 else 'poor',
                'issues': issues
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_monitor_performance(self) -> Dict:
        """Skill: Monitor system performance"""
        try:
            import time
            start_time = time.time()
            
            # Quick performance checks
            checks = {
                'blueprint_scan': 0,
                'file_check': 0,
                'database_check': 0
            }
            
            # Time blueprint scan
            scan_start = time.time()
            self.skill_check_blueprints()
            checks['blueprint_scan'] = time.time() - scan_start
            
            # Time file check
            file_start = time.time()
            self.skill_check_file_integrity()
            checks['file_check'] = time.time() - file_start
            
            # Time database check
            db_start = time.time()
            self.skill_verify_database()
            checks['database_check'] = time.time() - db_start
            
            total_time = time.time() - start_time
            
            self._record_skill_use('monitor_performance', {
                'total_time': total_time,
                'checks': checks
            })
            
            return {
                'success': True,
                'total_time': total_time,
                'checks': checks,
                'performance': 'excellent' if total_time < 1 else 'good' if total_time < 3 else 'fair'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_monitor_changes(self) -> Dict:
        """Skill: Monitor changes since last check"""
        try:
            # Get last check time from history
            last_check = None
            if self.history:
                last_check = max([h.get('timestamp', '') for h in self.history if 'timestamp' in h], default=None)
            
            changes = {
                'new_blueprints': 0,
                'new_routes': 0,
                'modified_files': 0
            }
            
            # This would compare with previous state
            # For now, return current state
            from backend.services.api_scanner import APIScanner
            scanner = APIScanner(self.base_dir)
            report = scanner.get_report()
            
            changes['current_blueprints'] = report['summary']['total_blueprints']
            changes['current_routes'] = report['summary']['total_routes']
            
            self._record_skill_use('monitor_changes', changes)
            
            return {
                'success': True,
                'last_check': last_check,
                'changes': changes
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== MISSION SYSTEM ==========
    
    def skill_create_mission(self, name: str, description: str, tasks: List[str]) -> Dict:
        """Skill: Create a new mission"""
        try:
            mission = {
                'id': f"mission_{len(self.missions) + 1}",
                'name': name,
                'description': description,
                'tasks': tasks,
                'status': 'active',
                'progress': 0,
                'created_at': datetime.now().isoformat(),
                'completed_at': None
            }
            
            self.missions.append(mission)
            self._save_json(self.missions_file, self.missions)
            
            self._record_skill_use('create_mission', {'mission_id': mission['id']})
            
            return {
                'success': True,
                'mission': mission
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_complete_mission(self, mission_id: str) -> Dict:
        """Skill: Complete a mission"""
        try:
            mission = next((m for m in self.missions if m['id'] == mission_id), None)
            if not mission:
                return {'success': False, 'error': 'Mission not found'}
            
            mission['status'] = 'completed'
            mission['progress'] = 100
            mission['completed_at'] = datetime.now().isoformat()
            
            self._save_json(self.missions_file, self.missions)
            self._record_skill_use('complete_mission', {'mission_id': mission_id})
            
            # Award experience
            self.personality['experience_level'] += 10
            self._save_json(self.personality_file, self.personality)
            
            return {
                'success': True,
                'mission': mission
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_get_missions(self, status: Optional[str] = None) -> Dict:
        """Skill: Get missions"""
        try:
            missions = self.missions
            if status:
                missions = [m for m in missions if m['status'] == status]
            
            return {
                'success': True,
                'missions': missions,
                'count': len(missions)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== QUEST SYSTEM ==========
    
    def skill_create_quest(self, name: str, description: str, objectives: List[Dict], reward: Dict) -> Dict:
        """Skill: Create a quest"""
        try:
            quest = {
                'id': f"quest_{len(self.quests) + 1}",
                'name': name,
                'description': description,
                'objectives': objectives,
                'reward': reward,
                'status': 'available',
                'progress': {},
                'started_at': None,
                'completed_at': None
            }
            
            self.quests.append(quest)
            self._save_json(self.quests_file, self.quests)
            
            self._record_skill_use('create_quest', {'quest_id': quest['id']})
            
            return {
                'success': True,
                'quest': quest
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_start_quest(self, quest_id: str) -> Dict:
        """Skill: Start a quest"""
        try:
            quest = next((q for q in self.quests if q['id'] == quest_id), None)
            if not quest:
                return {'success': False, 'error': 'Quest not found'}
            
            quest['status'] = 'in_progress'
            quest['started_at'] = datetime.now().isoformat()
            quest['progress'] = {obj['id']: 0 for obj in quest['objectives']}
            
            self._save_json(self.quests_file, self.quests)
            self._record_skill_use('start_quest', {'quest_id': quest_id})
            
            return {
                'success': True,
                'quest': quest
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_update_quest_progress(self, quest_id: str, objective_id: str, progress: int) -> Dict:
        """Skill: Update quest progress"""
        try:
            quest = next((q for q in self.quests if q['id'] == quest_id), None)
            if not quest:
                return {'success': False, 'error': 'Quest not found'}
            
            quest['progress'][objective_id] = progress
            
            # Check if all objectives complete
            all_complete = all(p >= 100 for p in quest['progress'].values())
            if all_complete:
                quest['status'] = 'completed'
                quest['completed_at'] = datetime.now().isoformat()
                
                # Award reward
                if 'experience' in quest['reward']:
                    self.personality['experience_level'] += quest['reward']['experience']
                if 'achievement' in quest['reward']:
                    self.personality['achievements'].append(quest['reward']['achievement'])
                self._save_json(self.personality_file, self.personality)
            
            self._save_json(self.quests_file, self.quests)
            
            return {
                'success': True,
                'quest': quest,
                'completed': all_complete
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_get_quests(self, status: Optional[str] = None) -> Dict:
        """Skill: Get quests"""
        try:
            quests = self.quests
            if status:
                quests = [q for q in quests if q['status'] == status]
            
            return {
                'success': True,
                'quests': quests,
                'count': len(quests)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== HISTORY SYSTEM ==========
    
    def _record_skill_use(self, skill_name: str, data: Dict):
        """Record skill use in history and award points"""
        entry = {
            'skill': skill_name,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        self.history.append(entry)
        
        # Keep last 1000 entries
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        
        self._save_json(self.history_file, self.history)
        
        # During a full diagnostic we skip point-awarding entirely. The award
        # path funnels into agent_trigger_system.award_points which can block
        # ~30s per call (a trigger/DB timeout in LITE production); running it
        # 8+ times serially made the diagnostic exceed the worker timeout.
        if getattr(self, '_suppress_point_award', False):
            return
        
        # Award points for skill execution - creates real value
        try:
            from backend.services.agent_point_creator import agent_point_creator
            user_id = data.get('user_id', 'agent_user') if isinstance(data, dict) else 'agent_user'
            agent_point_creator.award_points_for_agent_action(
                agent_id='master_fix_agent',
                action=skill_name,
                user_id=user_id
            )
        except Exception as e:
            pass  # Don't fail if point creation fails
    
    def skill_get_history(self, limit: int = 50, skill_filter: Optional[str] = None) -> Dict:
        """Skill: Get skill history"""
        try:
            history = self.history
            if skill_filter:
                history = [h for h in history if h.get('skill') == skill_filter]
            
            history = history[-limit:] if limit else history
            
            return {
                'success': True,
                'history': history,
                'count': len(history)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_get_statistics(self) -> Dict:
        """Skill: Get agent statistics"""
        try:
            # Count skill uses
            skill_counts = {}
            for entry in self.history:
                skill = entry.get('skill', 'unknown')
                skill_counts[skill] = skill_counts.get(skill, 0) + 1
            
            # Mission stats
            mission_stats = {
                'total': len(self.missions),
                'active': len([m for m in self.missions if m['status'] == 'active']),
                'completed': len([m for m in self.missions if m['status'] == 'completed'])
            }
            
            # Quest stats
            quest_stats = {
                'total': len(self.quests),
                'available': len([q for q in self.quests if q['status'] == 'available']),
                'in_progress': len([q for q in self.quests if q['status'] == 'in_progress']),
                'completed': len([q for q in self.quests if q['status'] == 'completed'])
            }
            
            return {
                'success': True,
                'skill_usage': skill_counts,
                'mission_stats': mission_stats,
                'quest_stats': quest_stats,
                'experience_level': self.personality.get('experience_level', 0),
                'achievements': len(self.personality.get('achievements', []))
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== PERSONALITY & BEHAVIOR ==========
    
    def skill_update_personality(self, updates: Dict) -> Dict:
        """Skill: Update agent personality"""
        try:
            self.personality.update(updates)
            self._save_json(self.personality_file, self.personality)
            
            return {
                'success': True,
                'personality': self.personality
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_get_personality(self) -> Dict:
        """Skill: Get agent personality"""
        return {
            'success': True,
            'personality': self.personality
        }
    
    def skill_apply_behavior_pattern(self, pattern_name: str) -> Dict:
        """Skill: Apply behavior pattern"""
        try:
            patterns = {
                'aggressive': {
                    'scan_frequency': 'high',
                    'auto_fix': True,
                    'detail_level': 'medium'
                },
                'cautious': {
                    'scan_frequency': 'low',
                    'auto_fix': False,
                    'detail_level': 'high'
                },
                'balanced': {
                    'scan_frequency': 'medium',
                    'auto_fix': False,
                    'detail_level': 'medium'
                }
            }
            
            if pattern_name not in patterns:
                return {'success': False, 'error': 'Unknown pattern'}
            
            pattern = patterns[pattern_name]
            self.personality['behavior_patterns'].update(pattern)
            self._save_json(self.personality_file, self.personality)
            
            return {
                'success': True,
                'pattern_applied': pattern_name,
                'personality': self.personality
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    # ========== DIAGNOSTIC SKILLS ==========
    
    def skill_run_full_diagnostic(self) -> Dict:
        """Skill: Run full system diagnostic"""
        try:
            import time as _time
            results = {}
            timings = {}
            self._suppress_point_award = True

            checks = [
                ('blueprints', self.skill_check_blueprints),
                ('database', self.skill_verify_database),
                ('file_integrity', self.skill_check_file_integrity),
                ('navigation', self.skill_check_navigation),
                ('missing_methods', self.skill_scan_missing_methods),
                ('service_health', self.skill_check_service_health),
                ('code_quality', self.skill_analyze_code_quality),
                ('system_health', self.skill_monitor_system_health),
            ]
            for name, fn in checks:
                _t = _time.time()
                try:
                    results[name] = fn()
                except Exception as e:
                    results[name] = {'success': False, 'error': str(e)}
                timings[name] = round(_time.time() - _t, 3)

            results['_timings'] = timings

            # Calculate overall health score
            health_score = results['system_health'].get('health_score', 0)
            
            self._record_skill_use('run_full_diagnostic', {
                'health_score': health_score,
                'checks_performed': len(results)
            })
            
            return {
                'success': True,
                'health_score': health_score,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            self._suppress_point_award = False
    
    # ========== CALCULATOR SKILLS ==========
    
    def _get_calculator(self):
        """Get calculator instance with database session"""
        try:
            from src.app import create_app
            from src.db.models import db
            from src.services.advanced_intelligent_calculator import AdvancedIntelligentCalculator
            
            # Try to get from Flask app context
            try:
                from flask import current_app
                if current_app:
                    with current_app.app_context():
                        calculator = AdvancedIntelligentCalculator(db.session)
                        return calculator, None
            except:
                pass
            
            # Fallback: create app context
            app = create_app()
            with app.app_context():
                calculator = AdvancedIntelligentCalculator(db.session)
                return calculator, app
        except Exception as e:
            return None, str(e)
    
    def skill_calculate_with_intelligence(self, user_id: str = 'agent_user') -> Dict:
        """Skill: Calculate points with intelligence"""
        try:
            calculator, app_context = self._get_calculator()
            if calculator is None:
                return {'success': False, 'error': f'Could not initialize calculator: {app_context}'}
            
            result = calculator.calculate_with_intelligence(user_id)
            
            self._record_skill_use('calculate_with_intelligence', {
                'user_id': user_id,
                'success': result.get('success', False)
            })
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_detect_point_loss(self, user_id: str = 'agent_user') -> Dict:
        """Skill: Detect point losses"""
        try:
            calculator, app_context = self._get_calculator()
            if calculator is None:
                return {'success': False, 'error': f'Could not initialize calculator: {app_context}'}
            
            result = calculator.detect_point_loss(user_id)
            
            self._record_skill_use('detect_point_loss', {
                'user_id': user_id,
                'success': result.get('success', False),
                'points_lost': result.get('points_lost', 0)
            })
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_repair_all_systems(self, user_id: str = 'agent_user') -> Dict:
        """Skill: Repair all systems"""
        try:
            calculator, app_context = self._get_calculator()
            if calculator is None:
                return {'success': False, 'error': f'Could not initialize calculator: {app_context}'}
            
            result = calculator.repair_all_systems(user_id)
            
            self._record_skill_use('repair_all_systems', {
                'user_id': user_id,
                'success': result.get('success', False),
                'points_restored': result.get('points_restored', 0)
            })
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_predict_future_points(self, user_id: str = 'agent_user', days: int = 30) -> Dict:
        """Skill: Predict future points"""
        try:
            calculator, app_context = self._get_calculator()
            if calculator is None:
                return {'success': False, 'error': f'Could not initialize calculator: {app_context}'}
            
            result = calculator.predict_future_points(user_id, days)
            
            self._record_skill_use('predict_future_points', {
                'user_id': user_id,
                'days': days,
                'success': result.get('success', False)
            })
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_analyze_patterns(self, user_id: str = 'agent_user') -> Dict:
        """Skill: Analyze patterns"""
        try:
            calculator, app_context = self._get_calculator()
            if calculator is None:
                return {'success': False, 'error': f'Could not initialize calculator: {app_context}'}
            
            result = calculator.analyze_patterns(user_id)
            
            self._record_skill_use('analyze_patterns', {
                'user_id': user_id,
                'success': result.get('success', False),
                'patterns_found': result.get('patterns_found', 0)
            })
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def skill_get_calculator_statistics(self, user_id: str = 'agent_user', days: int = 30) -> Dict:
        """Skill: Get calculator statistics"""
        try:
            calculator, app_context = self._get_calculator()
            if calculator is None:
                return {'success': False, 'error': f'Could not initialize calculator: {app_context}'}
            
            result = calculator.get_comprehensive_statistics(user_id, days)
            
            self._record_skill_use('get_calculator_statistics', {
                'user_id': user_id,
                'days': days,
                'success': result.get('success', False)
            })
            
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def initialize_calculator_missions_and_quests(self):
        """Initialize calculator missions and quests"""
        try:
            # Check if calculator missions/quests already exist
            existing_calc_missions = [m for m in self.missions if m.get('id', '').startswith('calc_mission')]
            existing_calc_quests = [q for q in self.quests if q.get('id', '').startswith('calc_quest')]
            
            if existing_calc_missions and existing_calc_quests:
                return {'success': True, 'message': 'Calculator missions and quests already exist'}
            
            # Create calculator missions
            calculator_missions = [
                {
                    'id': 'calc_mission_1',
                    'name': 'Intelligence Calculator Master',
                    'description': 'Perform 10 intelligent calculations',
                    'tasks': [
                        'calculate_with_intelligence (10 times)'
                    ],
                    'status': 'active',
                    'progress': 0,
                    'target': 10,
                    'reward': {'xp': 150, 'points': 1000},
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 'calc_mission_2',
                    'name': 'Loss Detection Specialist',
                    'description': 'Detect and analyze 5 point losses',
                    'tasks': [
                        'detect_point_loss (5 times)'
                    ],
                    'status': 'active',
                    'progress': 0,
                    'target': 5,
                    'reward': {'xp': 120, 'points': 800},
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 'calc_mission_3',
                    'name': 'System Repair Expert',
                    'description': 'Repair systems 3 times',
                    'tasks': [
                        'repair_all_systems (3 times)'
                    ],
                    'status': 'active',
                    'progress': 0,
                    'target': 3,
                    'reward': {'xp': 100, 'points': 600},
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 'calc_mission_4',
                    'name': 'Future Predictor',
                    'description': 'Make 5 predictions for different users',
                    'tasks': [
                        'predict_future_points (5 times)'
                    ],
                    'status': 'active',
                    'progress': 0,
                    'target': 5,
                    'reward': {'xp': 130, 'points': 900},
                    'created_at': datetime.now().isoformat()
                },
                {
                    'id': 'calc_mission_5',
                    'name': 'Pattern Analyzer',
                    'description': 'Analyze patterns for 3 users',
                    'tasks': [
                        'analyze_patterns (3 times)'
                    ],
                    'status': 'active',
                    'progress': 0,
                    'target': 3,
                    'reward': {'xp': 110, 'points': 700},
                    'created_at': datetime.now().isoformat()
                }
            ]
            
            # Add missions if they don't exist
            for mission in calculator_missions:
                if not any(m.get('id') == mission['id'] for m in self.missions):
                    self.missions.append(mission)
            
            # Create calculator quests
            calculator_quests = [
                {
                    'id': 'calc_quest_1',
                    'name': 'Calculator Master Quest',
                    'description': 'Complete all calculator skills',
                    'objectives': [
                        {'id': 'calc_intelligence', 'description': 'Perform intelligent calculation', 'target': 1},
                        {'id': 'calc_loss_detection', 'description': 'Detect point loss', 'target': 1},
                        {'id': 'calc_repair', 'description': 'Repair systems', 'target': 1},
                        {'id': 'calc_predict', 'description': 'Predict future points', 'target': 1},
                        {'id': 'calc_analyze', 'description': 'Analyze patterns', 'target': 1}
                    ],
                    'reward': {
                        'experience': 200,
                        'achievement': 'Calculator Master',
                        'points': 1500
                    },
                    'status': 'available',
                    'progress': {},
                    'started_at': None,
                    'completed_at': None
                },
                {
                    'id': 'calc_quest_2',
                    'name': 'Prediction Master Quest',
                    'description': 'Make predictions for 7, 30, and 90 days',
                    'objectives': [
                        {'id': 'predict_7', 'description': 'Predict 7 days ahead', 'target': 1},
                        {'id': 'predict_30', 'description': 'Predict 30 days ahead', 'target': 1},
                        {'id': 'predict_90', 'description': 'Predict 90 days ahead', 'target': 1}
                    ],
                    'reward': {
                        'experience': 180,
                        'achievement': 'Prediction Master',
                        'points': 1200
                    },
                    'status': 'available',
                    'progress': {},
                    'started_at': None,
                    'completed_at': None
                },
                {
                    'id': 'calc_quest_3',
                    'name': 'System Guardian Quest',
                    'description': 'Detect losses and repair systems',
                    'objectives': [
                        {'id': 'detect_loss', 'description': 'Detect point loss', 'target': 1},
                        {'id': 'repair_systems', 'description': 'Repair all systems', 'target': 1},
                        {'id': 'get_stats', 'description': 'Get calculator statistics', 'target': 1}
                    ],
                    'reward': {
                        'experience': 170,
                        'achievement': 'System Guardian',
                        'points': 1100
                    },
                    'status': 'available',
                    'progress': {},
                    'started_at': None,
                    'completed_at': None
                },
                {
                    'id': 'calc_quest_4',
                    'name': 'Pattern Analysis Expert',
                    'description': 'Analyze patterns and get statistics',
                    'objectives': [
                        {'id': 'analyze_patterns', 'description': 'Analyze patterns', 'target': 1},
                        {'id': 'get_statistics', 'description': 'Get calculator statistics', 'target': 1}
                    ],
                    'reward': {
                        'experience': 160,
                        'achievement': 'Pattern Expert',
                        'points': 1000
                    },
                    'status': 'available',
                    'progress': {},
                    'started_at': None,
                    'completed_at': None
                }
            ]
            
            # Add quests if they don't exist
            for quest in calculator_quests:
                if not any(q.get('id') == quest['id'] for q in self.quests):
                    self.quests.append(quest)
            
            # Save everything
            self._save_json(self.missions_file, self.missions)
            self._save_json(self.quests_file, self.quests)
            
            return {
                'success': True,
                'missions_added': len(calculator_missions) - len(existing_calc_missions),
                'quests_added': len(calculator_quests) - len(existing_calc_quests)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_all_skills(self) -> List[str]:
        """Get list of all available skills"""
        return [
            'check_blueprints',
            'verify_database',
            'check_file_integrity',
            'check_navigation',
            'scan_missing_methods',
            'check_service_health',
            'analyze_code_quality',
            'check_dependencies',
            'verify_endpoints',
            'monitor_api_structure',
            'monitor_system_health',
            'monitor_performance',
            'monitor_changes',
            'create_mission',
            'complete_mission',
            'get_missions',
            'create_quest',
            'start_quest',
            'update_quest_progress',
            'get_quests',
            'get_history',
            'get_statistics',
            'update_personality',
            'get_personality',
            'apply_behavior_pattern',
            'run_full_diagnostic',
            # Calculator skills
            'calculate_with_intelligence',
            'detect_point_loss',
            'repair_all_systems',
            'predict_future_points',
            'analyze_patterns',
            'get_calculator_statistics',
            # Python execution skills
            'execute_python_file',
            'execute_python_code',
            'list_python_scripts',
            'get_script_info',
            # Support and service skills
            'create_support_ticket',
            'get_support_tickets',
            'resolve_support_ticket',
            'get_services',
            'get_support_resources',
            # Research and monitoring skills
            'start_research',
            'collect_monitoring_data',
            'get_research_summary',
            'get_monitoring_summary',
            'award_points_trigger',
            'get_trigger_stats'
        ]

# Global instance
master_fix_agent_skills = MasterFixAgentSkills()
