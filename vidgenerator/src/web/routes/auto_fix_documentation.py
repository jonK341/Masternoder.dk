"""Auto-fix system based on debug results and documentation"""
from flask import Blueprint, jsonify, request
import os
import json
from datetime import datetime

auto_fix_doc_bp = Blueprint('auto_fix_doc', __name__)

# Documentation file for fixes
FIX_DOC_FILE = '/var/www/html/vidgenerator/auto_fix_documentation.json'

def load_fix_documentation():
    """Load fix documentation"""
    if os.path.exists(FIX_DOC_FILE):
        try:
            with open(FIX_DOC_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_fix_documentation(doc):
    """Save fix documentation"""
    try:
        with open(FIX_DOC_FILE, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2)
        return True
    except Exception as e:
        print(f"Error saving fix documentation: {e}")
        return False

def record_fix(issue_type, fix_applied, result, context=None):
    """Record a fix that was applied"""
    doc = load_fix_documentation()
    
    if 'fixes' not in doc:
        doc['fixes'] = []
    
    fix_entry = {
        'timestamp': datetime.now().isoformat(),
        'issue_type': issue_type,
        'fix_applied': fix_applied,
        'result': result,
        'context': context or {}
    }
    
    doc['fixes'].append(fix_entry)
    
    # Keep only last 100 fixes
    if len(doc['fixes']) > 100:
        doc['fixes'] = doc['fixes'][-100:]
    
    save_fix_documentation(doc)
    return fix_entry

@auto_fix_doc_bp.route('/api/debug/auto-fix-documented', methods=['POST'])
def auto_fix_documented():
    """Auto-fix with documentation"""
    try:
        data = request.get_json() or {}
        issue_type = data.get('issue_type', 'general')
        
        fixes_applied = []
        errors = []
        
        # Load known fixes from documentation
        doc = load_fix_documentation()
        known_fixes = doc.get('known_fixes', {})
        
        # Apply known fixes for this issue type
        if issue_type in known_fixes:
            for fix in known_fixes[issue_type]:
                try:
                    # Apply fix based on type
                    if fix['type'] == 'clear_cache':
                        import shutil
                        cache_path = fix.get('path', '/var/www/html/vidgenerator/__pycache__')
                        if os.path.exists(cache_path):
                            shutil.rmtree(cache_path)
                            fixes_applied.append(f"Cleared cache: {cache_path}")
                            record_fix(issue_type, fix['type'], 'success', {'path': cache_path})
                    
                    elif fix['type'] == 'restart_service':
                        import subprocess
                        service = fix.get('service', 'uwsgi-vidgenerator.service')
                        subprocess.run(['systemctl', 'restart', service], 
                                     capture_output=True, timeout=10)
                        fixes_applied.append(f"Restarted service: {service}")
                        record_fix(issue_type, fix['type'], 'success', {'service': service})
                    
                    elif fix['type'] == 'verify_file':
                        file_path = fix.get('path')
                        if file_path and os.path.exists(file_path):
                            fixes_applied.append(f"File verified: {file_path}")
                            record_fix(issue_type, fix['type'], 'success', {'path': file_path})
                        else:
                            errors.append(f"File missing: {file_path}")
                            record_fix(issue_type, fix['type'], 'failed', {'path': file_path})
                    
                except Exception as e:
                    errors.append(f"Fix failed: {str(e)}")
                    record_fix(issue_type, fix['type'], 'error', {'error': str(e)})
        
        return jsonify({
            'success': True,
            'fixes_applied': fixes_applied,
            'errors': errors,
            'documented': True
        })
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@auto_fix_doc_bp.route('/api/debug/fix-history', methods=['GET'])
def get_fix_history():
    """Get fix history"""
    try:
        doc = load_fix_documentation()
        limit = int(request.args.get('limit', 50))
        
        fixes = doc.get('fixes', [])
        return jsonify({
            'success': True,
            'fixes': fixes[-limit:],
            'total': len(fixes)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@auto_fix_doc_bp.route('/api/debug/add-known-fix', methods=['POST'])
def add_known_fix():
    """Add a known fix to documentation"""
    try:
        data = request.get_json()
        issue_type = data.get('issue_type')
        fix = data.get('fix')
        
        if not issue_type or not fix:
            return jsonify({'success': False, 'error': 'issue_type and fix required'}), 400
        
        doc = load_fix_documentation()
        
        if 'known_fixes' not in doc:
            doc['known_fixes'] = {}
        
        if issue_type not in doc['known_fixes']:
            doc['known_fixes'][issue_type] = []
        
        doc['known_fixes'][issue_type].append(fix)
        save_fix_documentation(doc)
        
        return jsonify({'success': True, 'message': 'Fix added to documentation'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

