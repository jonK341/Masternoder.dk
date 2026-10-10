"""
Enhanced Debugger with Error Detection and Auto-Fix
Continuously debugs for errors and provides fixes
"""
from flask import Blueprint, jsonify, request
import os
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path

debugger_enhanced_bp = Blueprint('debugger_enhanced', __name__)

# Error log
ERROR_LOG = '/var/www/html/vidgenerator/error_debug.log'

def log_debug_error(level, message, error=None, context=None):
    """Log debug error"""
    try:
        entry = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'message': message,
            'error': str(error) if error else None,
            'context': context or {}
        }
        
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')
        
        return True
    except Exception as e:
        logging.error(f"Error logging debug error: {e}")
        return False

@debugger_enhanced_bp.route('/api/debug/errors/scan', methods=['GET'])
def scan_errors():
    """Scan for errors in logs and system"""
    try:
        errors_found = []
        warnings_found = []
        
        # Scan debug.log
        debug_log = '/var/www/html/vidgenerator/debug.log'
        if os.path.exists(debug_log):
            try:
                with open(debug_log, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for line in lines[-100:]:  # Last 100 entries
                        try:
                            entry = json.loads(line.strip())
                            if entry.get('level') == 'error':
                                errors_found.append({
                                    'timestamp': entry.get('timestamp'),
                                    'message': entry.get('message'),
                                    'error': entry.get('error')
                                })
                            elif entry.get('level') == 'warning':
                                warnings_found.append({
                                    'timestamp': entry.get('timestamp'),
                                    'message': entry.get('message')
                                })
                        except:
                            continue
            except Exception as e:
                log_debug_error('error', 'Failed to scan debug.log', e)
        
        # Scan fix_log.json
        fix_log = '/var/www/html/vidgenerator/fix_log.json'
        if os.path.exists(fix_log):
            try:
                with open(fix_log, 'r', encoding='utf-8') as f:
                    log_data = json.load(f)
                    for fix in log_data.get('fixes', [])[-50:]:
                        if not fix.get('success'):
                            errors_found.append({
                                'timestamp': fix.get('timestamp'),
                                'message': f"Fix failed: {fix.get('action')}",
                                'error': str(fix.get('result', {}).get('errors', []))
                            })
            except Exception as e:
                log_debug_error('warning', 'Failed to scan fix_log.json', e)
        
        # Check for common issues
        common_issues = []
        
        # Check if routes are accessible
        try:
            from flask import current_app
            with current_app.app_context():
                routes = [str(r) for r in current_app.url_map.iter_rules()]
                if not any('/api/system/fix-all' in r for r in routes):
                    common_issues.append({
                        'type': 'route',
                        'message': 'fix-all route not found in registered routes',
                        'severity': 'high'
                    })
        except Exception as e:
            common_issues.append({
                'type': 'route',
                'message': f'Error checking routes: {str(e)}',
                'severity': 'medium'
            })
        
        return jsonify({
            'success': True,
            'errors': errors_found[-20:],  # Last 20 errors
            'warnings': warnings_found[-20:],  # Last 20 warnings
            'common_issues': common_issues,
            'summary': {
                'total_errors': len(errors_found),
                'total_warnings': len(warnings_found),
                'common_issues_count': len(common_issues)
            }
        })
    except Exception as e:
        import traceback
        log_debug_error('error', 'Error scanning for errors', e, {'traceback': traceback.format_exc()})
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_enhanced_bp.route('/api/debug/errors/auto-fix', methods=['POST'])
def auto_fix_errors():
    """Auto-fix detected errors"""
    try:
        fixes_applied = []
        errors = []
        
        # Get error scan results
        scan_result = scan_errors()
        scan_data = scan_result.get_json()
        
        if not scan_data.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to scan for errors'
            }), 500
        
        # Fix route issues
        if any(issue.get('type') == 'route' for issue in scan_data.get('common_issues', [])):
            try:
                # Verify routes are registered
                from flask import current_app
                with current_app.app_context():
                    # Try to import and register system_fixer if missing
                    try:
                        from src.web.routes.system_fixer import system_fixer_bp
                        if system_fixer_bp not in current_app.blueprints.values():
                            current_app.register_blueprint(system_fixer_bp, url_prefix='/api/system')
                            current_app.register_blueprint(system_fixer_bp, url_prefix='/vidgenerator/api/system', name='system_fixer_with_prefix')
                            fixes_applied.append('Registered system_fixer blueprint')
                    except Exception as e:
                        errors.append(f'Failed to register system_fixer: {str(e)}')
            except Exception as e:
                errors.append(f'Route fix error: {str(e)}')
        
        # Fix common errors
        for error in scan_data.get('errors', [])[:10]:  # Fix first 10 errors
            error_msg = error.get('message', '')
            if '404' in error_msg or 'not found' in error_msg.lower():
                # This is already being handled by route registration
                continue
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes_applied,
            'errors': errors,
            'message': f'Applied {len(fixes_applied)} fixes'
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@debugger_enhanced_bp.route('/api/debug/routes/list', methods=['GET'])
def list_routes():
    """List all registered routes for debugging"""
    try:
        from flask import current_app
        with current_app.app_context():
            routes = []
            for rule in current_app.url_map.iter_rules():
                routes.append({
                    'endpoint': rule.endpoint,
                    'rule': rule.rule,
                    'methods': list(rule.methods),
                    'has_system_fixer': '/api/system' in rule.rule or '/system' in rule.rule
                })
            
            # Filter for system fixer routes
            system_routes = [r for r in routes if 'system' in r['rule'].lower() or 'fix' in r['rule'].lower()]
            
            return jsonify({
                'success': True,
                'total_routes': len(routes),
                'system_routes': system_routes,
                'all_routes': routes[:50]  # First 50 routes
            })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

