"""
Comprehensive Debugger with Enhanced Options and Functional Logic
Reads logs, analyzes system, and provides recommendations
"""
from flask import Blueprint, jsonify, request
import os
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

comprehensive_debugger_bp = Blueprint('comprehensive_debugger', __name__)

# Log file paths
DEBUG_LOG = '/var/www/html/vidgenerator/debug.log'
AUTO_FIX_DOC = '/var/www/html/vidgenerator/auto_fix_documentation.json'
SYSTEM_LOG = '/var/www/html/vidgenerator/system.log'

class ComprehensiveDebugger:
    """Comprehensive debugger with enhanced options"""
    
    def __init__(self):
        self.analysis_results = {}
        self.recommendations = []
    
    def read_debug_log(self, limit: int = 100) -> List[Dict]:
        """Read debug log entries"""
        entries = []
        
        if os.path.exists(DEBUG_LOG):
            try:
                with open(DEBUG_LOG, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        try:
                            entry = json.loads(line.strip())
                            entries.append(entry)
                        except:
                            continue
            except Exception as e:
                logging.error(f"Error reading debug log: {e}")
        
        return entries
    
    def analyze_system(self) -> Dict[str, Any]:
        """Comprehensive system analysis"""
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'directory_structure': self._analyze_directory_structure(),
            'file_permissions': self._analyze_permissions(),
            'dependencies': self._analyze_dependencies(),
            'routes': self._analyze_routes(),
            'themes': self._analyze_themes(),
            'database': self._analyze_database(),
            'performance': self._analyze_performance(),
            'errors': self._analyze_errors(),
            'recommendations': []
        }
        
        # Generate recommendations
        analysis['recommendations'] = self._generate_recommendations(analysis)
        
        return analysis
    
    def _analyze_directory_structure(self) -> Dict:
        """Analyze directory structure"""
        base_path = Path('/var/www/html/vidgenerator')
        
        structure = {
            'base_path': str(base_path),
            'exists': base_path.exists(),
            'subdirectories': {},
            'issues': []
        }
        
        if base_path.exists():
            key_dirs = [
                'src',
                'src/web',
                'src/web/routes',
                'src/web/templates',
                'src/web/static',
                'src/services',
                'src/db',
                'output'
            ]
            
            for dir_path in key_dirs:
                full_path = base_path / dir_path
                structure['subdirectories'][dir_path] = {
                    'exists': full_path.exists(),
                    'writable': os.access(full_path, os.W_OK) if full_path.exists() else False
                }
                
                if not full_path.exists():
                    structure['issues'].append(f'Missing directory: {dir_path}')
        
        return structure
    
    def _analyze_permissions(self) -> Dict:
        """Analyze file permissions"""
        base_path = Path('/var/www/html/vidgenerator')
        
        permissions = {
            'issues': [],
            'warnings': []
        }
        
        if base_path.exists():
            # Check key files
            key_files = [
                'src/app.py',
                'wsgi.py',
                'src/web/routes/__init__.py'
            ]
            
            for file_path in key_files:
                full_path = base_path / file_path
                if full_path.exists():
                    stat = os.stat(full_path)
                    mode = oct(stat.st_mode)[-3:]
                    if mode != '644' and mode != '755':
                        permissions['warnings'].append(f'{file_path}: {mode}')
        
        return permissions
    
    def _analyze_dependencies(self) -> Dict:
        """Analyze Python dependencies"""
        dependencies = {
            'required': ['flask', 'sqlalchemy', 'werkzeug'],
            'installed': [],
            'missing': [],
            'issues': []
        }
        
        try:
            import pkg_resources
            installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
            
            for req in dependencies['required']:
                if req.lower() in installed_packages:
                    dependencies['installed'].append(f'{req}=={installed_packages[req.lower()]}')
                else:
                    dependencies['missing'].append(req)
                    dependencies['issues'].append(f'Missing dependency: {req}')
        except Exception as e:
            dependencies['issues'].append(f'Error checking dependencies: {e}')
        
        return dependencies
    
    def _analyze_routes(self) -> Dict:
        """Analyze Flask routes"""
        routes = {
            'total': 0,
            'by_prefix': {},
            'issues': []
        }
        
        try:
            from flask import current_app
            with current_app.app_context():
                all_routes = list(current_app.url_map.iter_rules())
                routes['total'] = len(all_routes)
                
                for route in all_routes:
                    prefix = route.rule.split('/')[1] if len(route.rule.split('/')) > 1 else 'root'
                    routes['by_prefix'][prefix] = routes['by_prefix'].get(prefix, 0) + 1
        except Exception as e:
            routes['issues'].append(f'Error analyzing routes: {e}')
        
        return routes
    
    def _analyze_themes(self) -> Dict:
        """Analyze theme system"""
        themes = {
            'total': 0,
            'configured': [],
            'missing_files': [],
            'issues': []
        }
        
        try:
            from src.services.theme_manager.theme_config import ThemeConfig
            theme_config = ThemeConfig()
            
            theme_list = ['matrix', 'cyberpunk', 'sci-fi', 'nature', 'mtg', 'halo4', 'wwii']
            
            for theme_name in theme_list:
                theme = theme_config.get_theme(theme_name)
                if theme:
                    themes['configured'].append(theme_name)
                    themes['total'] += 1
                    
                    # Check files
                    video_path = theme.get('background_video', '')
                    if video_path:
                        full_path = Path('/var/www/html/vidgenerator') / video_path.lstrip('/')
                        if not full_path.exists():
                            themes['missing_files'].append(f'{theme_name}: {video_path}')
                else:
                    themes['issues'].append(f'Theme not configured: {theme_name}')
        except Exception as e:
            themes['issues'].append(f'Error analyzing themes: {e}')
        
        return themes
    
    def _analyze_database(self) -> Dict:
        """Analyze database"""
        database = {
            'connected': False,
            'tables': [],
            'issues': []
        }
        
        try:
            from src.db.models import db
            from sqlalchemy import inspect
            
            inspector = inspect(db.engine)
            database['tables'] = inspector.get_table_names()
            database['connected'] = True
        except Exception as e:
            database['issues'].append(f'Database error: {e}')
        
        return database
    
    def _analyze_performance(self) -> Dict:
        """Analyze performance metrics"""
        performance = {
            'log_file_size': 0,
            'cache_size': 0,
            'issues': []
        }
        
        if os.path.exists(DEBUG_LOG):
            performance['log_file_size'] = os.path.getsize(DEBUG_LOG)
            if performance['log_file_size'] > 10 * 1024 * 1024:  # > 10MB
                performance['issues'].append('Debug log file is very large, consider rotation')
        
        return performance
    
    def _analyze_errors(self) -> Dict:
        """Analyze errors from logs"""
        errors = {
            'total': 0,
            'by_type': {},
            'recent': []
        }
        
        log_entries = self.read_debug_log(limit=500)
        
        for entry in log_entries:
            if entry.get('level') == 'error':
                errors['total'] += 1
                error_type = entry.get('error', 'unknown')
                errors['by_type'][error_type] = errors['by_type'].get(error_type, 0) + 1
        
        errors['recent'] = [e for e in log_entries if e.get('level') == 'error'][-10:]
        
        return errors
    
    def _generate_recommendations(self, analysis: Dict) -> List[Dict]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Directory structure recommendations
        if analysis['directory_structure']['issues']:
            recommendations.append({
                'type': 'structure',
                'priority': 'high',
                'message': 'Missing directories detected',
                'action': 'Create missing directories',
                'details': analysis['directory_structure']['issues']
            })
        
        # Dependency recommendations
        if analysis['dependencies']['missing']:
            recommendations.append({
                'type': 'dependencies',
                'priority': 'high',
                'message': 'Missing dependencies',
                'action': 'Install missing packages',
                'details': analysis['dependencies']['missing']
            })
        
        # Theme recommendations
        if analysis['themes']['missing_files']:
            recommendations.append({
                'type': 'themes',
                'priority': 'medium',
                'message': 'Theme files missing',
                'action': 'Generate or restore theme assets',
                'details': analysis['themes']['missing_files']
            })
        
        # Performance recommendations
        if analysis['performance']['issues']:
            recommendations.append({
                'type': 'performance',
                'priority': 'low',
                'message': 'Performance issues detected',
                'action': 'Optimize or rotate logs',
                'details': analysis['performance']['issues']
            })
        
        # Error recommendations
        if analysis['errors']['total'] > 100:
            recommendations.append({
                'type': 'errors',
                'priority': 'high',
                'message': 'High error count detected',
                'action': 'Review and fix common errors',
                'details': f"Total errors: {analysis['errors']['total']}"
            })
        
        # Location recommendation
        current_path = analysis['directory_structure']['base_path']
        if '/var/www/html/vidgenerator' in current_path:
            recommendations.append({
                'type': 'location',
                'priority': 'medium',
                'message': 'Consider alternative directory structure',
                'action': 'Evaluate moving to /opt/vidgenerator or /srv/vidgenerator',
                'details': 'Current location may have permission issues or be less organized'
            })
        
        return recommendations
    
    def generate_migration_report(self) -> Dict[str, Any]:
        """Generate report on whether to migrate or fix"""
        analysis = self.analyze_system()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'current_location': analysis['directory_structure']['base_path'],
            'analysis': analysis,
            'migration_recommendation': self._evaluate_migration(analysis),
            'fix_recommendation': self._evaluate_fixes(analysis),
            'action_plan': []
        }
        
        # Generate action plan
        if report['migration_recommendation']['should_migrate']:
            report['action_plan'] = self._generate_migration_plan()
        else:
            report['action_plan'] = self._generate_fix_plan(analysis)
        
        return report
    
    def _evaluate_migration(self, analysis: Dict) -> Dict:
        """Evaluate if migration is recommended"""
        score = 0
        reasons = []
        
        # Check directory issues
        if len(analysis['directory_structure']['issues']) > 5:
            score += 2
            reasons.append('Multiple directory structure issues')
        
        # Check permission issues
        if len(analysis['file_permissions']['issues']) > 3:
            score += 2
            reasons.append('Permission issues detected')
        
        # Check error rate
        if analysis['errors']['total'] > 200:
            score += 3
            reasons.append('High error rate')
        
        # Check theme issues
        if len(analysis['themes']['issues']) > 3:
            score += 1
            reasons.append('Multiple theme issues')
        
        should_migrate = score >= 5
        
        return {
            'should_migrate': should_migrate,
            'score': score,
            'reasons': reasons,
            'alternative_locations': [
                '/opt/vidgenerator',
                '/srv/vidgenerator',
                '/home/vidgenerator/app'
            ]
        }
    
    def _evaluate_fixes(self, analysis: Dict) -> Dict:
        """Evaluate if fixing is recommended"""
        fixable_issues = 0
        critical_issues = 0
        
        # Count fixable issues
        fixable_issues += len(analysis['directory_structure']['issues'])
        fixable_issues += len(analysis['dependencies']['missing'])
        fixable_issues += len(analysis['themes']['missing_files'])
        
        # Count critical issues
        if analysis['dependencies']['missing']:
            critical_issues += 1
        if analysis['database']['issues']:
            critical_issues += 1
        
        return {
            'fixable': fixable_issues,
            'critical': critical_issues,
            'recommended': fixable_issues < 20 and critical_issues < 3
        }
    
    def _generate_migration_plan(self) -> List[Dict]:
        """Generate migration plan"""
        return [
            {
                'step': 1,
                'action': 'Backup current installation',
                'command': 'tar -czf /backup/vidgenerator_backup_$(date +%Y%m%d).tar.gz /var/www/html/vidgenerator'
            },
            {
                'step': 2,
                'action': 'Create new directory structure',
                'command': 'mkdir -p /opt/vidgenerator/{src,output,logs,static}'
            },
            {
                'step': 3,
                'action': 'Copy files to new location',
                'command': 'cp -r /var/www/html/vidgenerator/* /opt/vidgenerator/'
            },
            {
                'step': 4,
                'action': 'Update configuration files',
                'command': 'Update paths in config files'
            },
            {
                'step': 5,
                'action': 'Update systemd service',
                'command': 'Update uwsgi-vidgenerator.service with new paths'
            },
            {
                'step': 6,
                'action': 'Update Apache/Nginx config',
                'command': 'Update proxy configuration'
            },
            {
                'step': 7,
                'action': 'Test new installation',
                'command': 'Run comprehensive tests'
            },
            {
                'step': 8,
                'action': 'Switch over',
                'command': 'Restart services and verify'
            }
        ]
    
    def _generate_fix_plan(self, analysis: Dict) -> List[Dict]:
        """Generate fix plan"""
        plan = []
        
        # Fix directory structure
        if analysis['directory_structure']['issues']:
            plan.append({
                'step': 1,
                'action': 'Create missing directories',
                'details': analysis['directory_structure']['issues']
            })
        
        # Fix dependencies
        if analysis['dependencies']['missing']:
            plan.append({
                'step': 2,
                'action': 'Install missing dependencies',
                'command': f"pip install {' '.join(analysis['dependencies']['missing'])}"
            })
        
        # Fix themes
        if analysis['themes']['missing_files']:
            plan.append({
                'step': 3,
                'action': 'Generate theme assets',
                'command': 'POST /api/theme/generate-all-assets'
            })
        
        # Fix permissions
        if analysis['file_permissions']['issues']:
            plan.append({
                'step': 4,
                'action': 'Fix file permissions',
                'command': 'chmod -R 755 /var/www/html/vidgenerator'
            })
        
        return plan

# Initialize debugger
debugger = ComprehensiveDebugger()

@comprehensive_debugger_bp.route('/api/debug/comprehensive/analyze', methods=['GET'])
def comprehensive_analyze():
    """Comprehensive system analysis"""
    try:
        result = debugger.analyze_system()
        return jsonify(result)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@comprehensive_debugger_bp.route('/api/debug/comprehensive/logs', methods=['GET'])
def get_comprehensive_logs():
    """Get comprehensive log analysis"""
    try:
        limit = int(request.args.get('limit', 100))
        entries = debugger.read_debug_log(limit=limit)
        
        # Analyze logs
        analysis = {
            'total_entries': len(entries),
            'by_level': {},
            'recent_errors': [],
            'recent_warnings': []
        }
        
        for entry in entries:
            level = entry.get('level', 'info')
            analysis['by_level'][level] = analysis['by_level'].get(level, 0) + 1
            
            if level == 'error':
                analysis['recent_errors'].append(entry)
            elif level == 'warning':
                analysis['recent_warnings'].append(entry)
        
        return jsonify({
            'success': True,
            'entries': entries,
            'analysis': analysis
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@comprehensive_debugger_bp.route('/api/debug/comprehensive/migration-report', methods=['GET'])
def get_migration_report():
    """Get migration vs fix recommendation report"""
    try:
        report = debugger.generate_migration_report()
        return jsonify(report)
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@comprehensive_debugger_bp.route('/api/debug/comprehensive/fix-themes', methods=['POST'])
def fix_all_themes():
    """Fix all theme building"""
    try:
        from src.services.theme_manager.theme_debugger_engine import ThemeDebuggerEngine
        
        theme_debugger = ThemeDebuggerEngine()
        
        # Debug all themes
        debug_results = theme_debugger.debug_all_themes()
        
        # Generate assets for all themes
        asset_results = theme_debugger.generate_all_theme_assets()
        
        return jsonify({
            'success': True,
            'debug_results': debug_results,
            'asset_results': asset_results,
            'message': 'Theme building fixed and assets generated'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

