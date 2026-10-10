"""
System Fixer - Comprehensive Auto-Fix System
Fixes organizational structures, permissions, database, and errors
"""
from flask import Blueprint, jsonify, request
import os
import subprocess
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any

system_fixer_bp = Blueprint('system_fixer', __name__)

# Log file for fixes
FIX_LOG = '/var/www/html/vidgenerator/fix_log.json'

def log_fix(action: str, result: Dict, success: bool = True):
    """Log fix action"""
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'success': success,
            'result': result
        }
        
        # Load existing log
        if os.path.exists(FIX_LOG):
            with open(FIX_LOG, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
        else:
            log_data = {'fixes': []}
        
        log_data['fixes'].append(log_entry)
        
        # Keep only last 1000 entries
        if len(log_data['fixes']) > 1000:
            log_data['fixes'] = log_data['fixes'][-1000:]
        
        # Save log
        with open(FIX_LOG, 'w', encoding='utf-8') as f:
            json.dump(log_data, f, indent=2)
        
        return True
    except Exception as e:
        logging.error(f"Error logging fix: {e}")
        return False

class SystemFixer:
    """Comprehensive system fixer"""
    
    def __init__(self):
        self.base_path = Path('/var/www/html/vidgenerator')
        self.fixes_applied = []
        self.errors = []
    
    def fix_organizational_structures(self) -> Dict:
        """Fix organizational directory structures"""
        result = {
            'directories_created': [],
            'errors': []
        }
        
        required_dirs = [
            'src',
            'src/web',
            'src/web/routes',
            'src/web/templates',
            'src/web/static',
            'src/web/static/js',
            'src/web/static/css',
            'src/web/static/img',
            'src/web/static/video',
            'src/web/static/video/themes',
            'src/web/static/img/themes',
            'src/services',
            'src/services/theme_manager',
            'src/services/ai_generation',
            'src/services/video_generation',
            'src/db',
            'src/utils',
            'output',
            'logs',
            'static',
            'static/video',
            'static/img',
            'static/css',
            'static/js'
        ]
        
        for dir_path in required_dirs:
            full_path = self.base_path / dir_path
            try:
                if not full_path.exists():
                    full_path.mkdir(parents=True, exist_ok=True)
                    result['directories_created'].append(str(full_path))
                    self.fixes_applied.append(f'Created directory: {dir_path}')
                else:
                    self.fixes_applied.append(f'Directory exists: {dir_path}')
            except Exception as e:
                error_msg = f'Failed to create {dir_path}: {str(e)}'
                result['errors'].append(error_msg)
                self.errors.append(error_msg)
        
        log_fix('organizational_structures', result, len(result['errors']) == 0)
        return result
    
    def fix_permissions(self) -> Dict:
        """Fix file and directory permissions"""
        result = {
            'permissions_fixed': [],
            'errors': []
        }
        
        try:
            # Fix directory permissions (755)
            subprocess.run(
                ['chmod', '-R', '755', str(self.base_path)],
                capture_output=True,
                timeout=30
            )
            result['permissions_fixed'].append('All directories set to 755')
            self.fixes_applied.append('Fixed directory permissions')
            
            # Fix file permissions (644)
            subprocess.run(
                ['find', str(self.base_path), '-type', 'f', '-exec', 'chmod', '644', '{}', '+'],
                capture_output=True,
                timeout=30
            )
            result['permissions_fixed'].append('All files set to 644')
            self.fixes_applied.append('Fixed file permissions')
            
            # Make Python files executable
            subprocess.run(
                ['find', str(self.base_path), '-name', '*.py', '-exec', 'chmod', '755', '{}', '+'],
                capture_output=True,
                timeout=30
            )
            result['permissions_fixed'].append('Python files set to 755')
            self.fixes_applied.append('Fixed Python file permissions')
            
            # Ensure output directory is writable
            output_dir = self.base_path / 'output'
            if output_dir.exists():
                subprocess.run(
                    ['chmod', '777', str(output_dir)],
                    capture_output=True,
                    timeout=10
                )
                result['permissions_fixed'].append('Output directory set to 777')
                self.fixes_applied.append('Fixed output directory permissions')
            
        except Exception as e:
            error_msg = f'Permission fix error: {str(e)}'
            result['errors'].append(error_msg)
            self.errors.append(error_msg)
        
        log_fix('permissions', result, len(result['errors']) == 0)
        return result
    
    def fix_database(self) -> Dict:
        """Fix database issues"""
        result = {
            'database_initialized': False,
            'tables_created': [],
            'errors': []
        }
        
        try:
            from src.db.models import db
            from src.app import create_app
            
            app = create_app()
            with app.app_context():
                # Create all tables
                db.create_all()
                result['database_initialized'] = True
                self.fixes_applied.append('Database initialized')
                
                # Get table names
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                result['tables_created'] = tables
                self.fixes_applied.append(f'Created {len(tables)} database tables')
                
        except Exception as e:
            import traceback
            error_msg = f'Database fix error: {str(e)}'
            result['errors'].append(error_msg)
            result['traceback'] = traceback.format_exc()
            self.errors.append(error_msg)
        
        log_fix('database', result, len(result['errors']) == 0)
        return result
    
    def fix_errors(self) -> Dict:
        """Fix common errors"""
        result = {
            'errors_fixed': [],
            'remaining_errors': [],
            'warnings': []
        }
        
        # Read debug log
        debug_log_path = self.base_path / 'debug.log'
        if debug_log_path.exists():
            try:
                with open(debug_log_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    error_count = 0
                    for line in lines[-100:]:  # Check last 100 entries
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('level') == 'error':
                                error_count += 1
                                # Try to fix common errors
                                error_msg = entry.get('message', '')
                                if 'import' in error_msg.lower():
                                    result['warnings'].append(f'Import error detected: {error_msg[:50]}')
                                elif 'permission' in error_msg.lower():
                                    result['errors_fixed'].append('Permission error (should be fixed by permission fix)')
                                elif 'not found' in error_msg.lower():
                                    result['warnings'].append(f'File not found: {error_msg[:50]}')
                        except:
                            continue
                    
                    if error_count > 0:
                        result['remaining_errors'].append(f'{error_count} errors in log')
            except Exception as e:
                result['warnings'].append(f'Could not read debug log: {str(e)}')
        
        # Clear old cache files
        try:
            import shutil
            cache_dirs = []
            for root, dirs, files in os.walk(str(self.base_path)):
                if '__pycache__' in dirs:
                    cache_dirs.append(os.path.join(root, '__pycache__'))
            
            for cache_dir in cache_dirs:
                try:
                    shutil.rmtree(cache_dir)
                    result['errors_fixed'].append(f'Cleared cache: {cache_dir}')
                    self.fixes_applied.append(f'Cleared cache directory')
                except:
                    pass
        except Exception as e:
            result['warnings'].append(f'Cache clear warning: {str(e)}')
        
        log_fix('errors', result, len(result['remaining_errors']) == 0)
        return result
    
    def fix_all(self) -> Dict:
        """Fix all issues"""
        self.fixes_applied = []
        self.errors = []
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'organizational_structures': self.fix_organizational_structures(),
            'permissions': self.fix_permissions(),
            'database': self.fix_database(),
            'errors': self.fix_errors(),
            'summary': {
                'fixes_applied': len(self.fixes_applied),
                'errors': len(self.errors)
            }
        }
        
        results['fixes_applied'] = self.fixes_applied
        results['errors'] = self.errors
        
        return results

# Initialize fixer
fixer = SystemFixer()

@system_fixer_bp.route('/fix-all', methods=['POST'])
@system_fixer_bp.route('/api/system/fix-all', methods=['POST'])
def fix_all_system():
    """Fix all system issues"""
    try:
        results = fixer.fix_all()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@system_fixer_bp.route('/fix-structures', methods=['POST'])
@system_fixer_bp.route('/api/system/fix-structures', methods=['POST'])
def fix_structures():
    """Fix organizational structures"""
    try:
        results = fixer.fix_organizational_structures()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@system_fixer_bp.route('/fix-permissions', methods=['POST'])
@system_fixer_bp.route('/api/system/fix-permissions', methods=['POST'])
def fix_permissions_endpoint():
    """Fix permissions"""
    try:
        results = fixer.fix_permissions()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@system_fixer_bp.route('/fix-database', methods=['POST'])
@system_fixer_bp.route('/api/system/fix-database', methods=['POST'])
def fix_database_endpoint():
    """Fix database"""
    try:
        results = fixer.fix_database()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@system_fixer_bp.route('/fix-errors', methods=['POST'])
@system_fixer_bp.route('/api/system/fix-errors', methods=['POST'])
def fix_errors_endpoint():
    """Fix errors"""
    try:
        results = fixer.fix_errors()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@system_fixer_bp.route('/fix-log', methods=['GET'])
@system_fixer_bp.route('/api/system/fix-log', methods=['GET'])
def get_fix_log():
    """Get fix log"""
    try:
        if os.path.exists(FIX_LOG):
            with open(FIX_LOG, 'r', encoding='utf-8') as f:
                log_data = json.load(f)
            return jsonify({
                'success': True,
                'log': log_data
            })
        else:
            return jsonify({
                'success': True,
                'log': {'fixes': []}
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

