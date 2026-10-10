"""
Documentation System API
Comprehensive documentation for fixes, improvements, and system knowledge
"""

from flask import Blueprint, jsonify, request, render_template
from datetime import datetime
import json
import os
from pathlib import Path

documentation_api_bp = Blueprint('documentation_api', __name__)

DOCS_DIR = '/var/www/html/vidgenerator/docs'
FIXES_LOG = '/var/www/html/vidgenerator/fix_log.json'
IMPROVEMENTS_LOG = '/var/www/html/vidgenerator/improvements_log.json'

def ensure_docs_dir():
    """Ensure documentation directory exists"""
    os.makedirs(DOCS_DIR, exist_ok=True)
    return DOCS_DIR

def load_json_file(filepath, default=None):
    """Load JSON file safely"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default or {}
    except Exception as e:
        print(f"[DocumentationAPI] Error loading {filepath}: {e}")
        return default or {}

def save_json_file(filepath, data):
    """Save JSON file safely"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[DocumentationAPI] Error saving {filepath}: {e}")
        return False

@documentation_api_bp.route('/api/docs/fixes', methods=['GET'])
def get_fixes():
    """Get all documented fixes"""
    try:
        fixes = load_json_file(FIXES_LOG, {'fixes': []})
        return jsonify({
            'success': True,
            'fixes': fixes.get('fixes', []),
            'total': len(fixes.get('fixes', []))
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@documentation_api_bp.route('/api/docs/improvements', methods=['GET'])
def get_improvements():
    """Get all documented improvements"""
    try:
        improvements = load_json_file(IMPROVEMENTS_LOG, {'improvements': []})
        return jsonify({
            'success': True,
            'improvements': improvements.get('improvements', []),
            'total': len(improvements.get('improvements', []))
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@documentation_api_bp.route('/api/docs/add', methods=['POST'])
def add_documentation():
    """Add new documentation entry"""
    try:
        data = request.get_json()
        doc_type = data.get('type', 'improvement')  # 'fix' or 'improvement'
        title = data.get('title', '')
        description = data.get('description', '')
        category = data.get('category', 'general')
        tags = data.get('tags', [])
        
        if not title:
            return jsonify({
                'success': False,
                'error': 'Title is required'
            }), 400
        
        entry = {
            'id': f"doc_{datetime.now().timestamp()}",
            'type': doc_type,
            'title': title,
            'description': description,
            'category': category,
            'tags': tags,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        if doc_type == 'fix':
            filepath = FIXES_LOG
            data_key = 'fixes'
        else:
            filepath = IMPROVEMENTS_LOG
            data_key = 'improvements'
        
        existing_data = load_json_file(filepath, {data_key: []})
        existing_data[data_key].append(entry)
        save_json_file(filepath, existing_data)
        
        return jsonify({
            'success': True,
            'entry': entry
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@documentation_api_bp.route('/api/docs/search', methods=['GET'])
def search_documentation():
    """Search documentation by query"""
    try:
        query = request.args.get('q', '').lower()
        category = request.args.get('category', None)
        doc_type = request.args.get('type', None)
        
        results = []
        
        # Search fixes
        if not doc_type or doc_type == 'fix':
            fixes = load_json_file(FIXES_LOG, {'fixes': []})
            for fix in fixes.get('fixes', []):
                if (not category or fix.get('category') == category) and \
                   (not query or query in fix.get('title', '').lower() or query in fix.get('description', '').lower()):
                    results.append(fix)
        
        # Search improvements
        if not doc_type or doc_type == 'improvement':
            improvements = load_json_file(IMPROVEMENTS_LOG, {'improvements': []})
            for improvement in improvements.get('improvements', []):
                if (not category or improvement.get('category') == category) and \
                   (not query or query in improvement.get('title', '').lower() or query in improvement.get('description', '').lower()):
                    results.append(improvement)
        
        return jsonify({
            'success': True,
            'results': results,
            'total': len(results)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@documentation_api_bp.route('/api/docs/categories', methods=['GET'])
def get_categories():
    """Get all documentation categories"""
    try:
        fixes = load_json_file(FIXES_LOG, {'fixes': []})
        improvements = load_json_file(IMPROVEMENTS_LOG, {'improvements': []})
        
        categories = set()
        for fix in fixes.get('fixes', []):
            if fix.get('category'):
                categories.add(fix.get('category'))
        for improvement in improvements.get('improvements', []):
            if improvement.get('category'):
                categories.add(improvement.get('category'))
        
        return jsonify({
            'success': True,
            'categories': sorted(list(categories))
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@documentation_api_bp.route('/api/docs/stats', methods=['GET'])
def get_documentation_stats():
    """Get documentation statistics"""
    try:
        fixes = load_json_file(FIXES_LOG, {'fixes': []})
        improvements = load_json_file(IMPROVEMENTS_LOG, {'improvements': []})
        
        fixes_list = fixes.get('fixes', [])
        improvements_list = improvements.get('improvements', [])
        
        # Count by category
        category_counts = {}
        for fix in fixes_list:
            cat = fix.get('category', 'general')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        for improvement in improvements_list:
            cat = improvement.get('category', 'general')
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Count by type
        type_counts = {
            'fixes': len(fixes_list),
            'improvements': len(improvements_list),
            'total': len(fixes_list) + len(improvements_list)
        }
        
        return jsonify({
            'success': True,
            'stats': {
                'total': type_counts['total'],
                'fixes': type_counts['fixes'],
                'improvements': type_counts['improvements'],
                'categories': category_counts
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@documentation_api_bp.route('/docs', methods=['GET'])
@documentation_api_bp.route('/vidgenerator/docs', methods=['GET'])
def documentation_page():
    """Render documentation page"""
    return render_template('documentation/index.html')

