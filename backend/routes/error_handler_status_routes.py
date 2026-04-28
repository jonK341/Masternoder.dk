"""
Error Handler Status API Routes
Provides analysis of error handlers across the codebase
"""
from flask import Blueprint, jsonify
import os
import re
from pathlib import Path
from collections import defaultdict

error_handler_status_bp = Blueprint('error_handler_status', __name__)


def analyze_error_handlers():
    """
    Analyze error handlers in JavaScript files
    Returns statistics about error handler usage and migration status
    This is a standalone function that can be imported by other modules
    """
    try:
        # Scan all project static/js trees (root + legacy vidgenerator path + server deploy path)
        search_roots = [
            Path('static/js'),
            Path('vidgenerator/static/js'),
            Path('/var/www/html/vidgenerator/static/js'),
            Path('/var/www/html/static/js'),
        ]
        seen_paths = set()
        js_files = []
        for root in search_roots:
            if not root.exists() or not root.is_dir():
                continue
            for js_file in root.glob('*.js'):
                key = str(js_file.resolve())
                if key in seen_paths:
                    continue
                seen_paths.add(key)
                js_files.append(js_file)

        if not js_files:
            return {
                'success': False,
                'error': 'JavaScript directory not found (tried static/js and vidgenerator/static/js)'
            }
        
        error_patterns = {
            'console.error': r'console\.error',
            'console.warn': r'console\.warn',
            'catch_blocks': r'catch\s*\([^)]*\)',
            'promise_catch': r'\.catch\s*\(',
            'try_blocks': r'try\s*\{',
        }
        
        stats = {
            'total_files': 0,
            'files_analyzed': 0,
            'files_with_error_manager': 0,
            'files_without_error_manager': 0,
            'total_handlers': 0,
            'handler_types': defaultdict(int),
            'files': [],
            'top_files_needing_migration': []
        }
        
        stats['total_files'] = len(js_files)
        stats['scanned_roots'] = sorted({str(p.parent) for p in js_files})
        
        for js_file in js_files:
            stats['files_analyzed'] += 1
            try:
                with open(js_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                file_stats = {
                    'name': js_file.name,
                    'handlers': 0,
                    'has_error_manager': False
                }
                
                # Check if using ErrorManager
                has_error_manager = 'ErrorManager' in content or 'error-manager' in content
                file_stats['has_error_manager'] = has_error_manager
                
                if has_error_manager:
                    stats['files_with_error_manager'] += 1
                else:
                    stats['files_without_error_manager'] += 1
                
                # Count handlers
                for pattern_name, pattern in error_patterns.items():
                    matches = len(re.findall(pattern, content, re.IGNORECASE))
                    file_stats['handlers'] += matches
                    stats['handler_types'][pattern_name] += matches
                
                stats['total_handlers'] += file_stats['handlers']
                
                if file_stats['handlers'] > 0:
                    stats['files'].append(file_stats)
                    
            except Exception as e:
                continue
        
        # Sort files by handler count
        stats['files'].sort(key=lambda x: x['handlers'], reverse=True)
        
        # Get top files needing migration (have handlers but no ErrorManager)
        stats['top_files_needing_migration'] = [
            f for f in stats['files'] 
            if f['handlers'] > 0 and not f['has_error_manager']
        ][:20]
        
        # Convert defaultdict to regular dict for JSON
        stats['handler_types'] = dict(stats['handler_types'])
        
        return {
            'success': True,
            'analysis': stats
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@error_handler_status_bp.route('/api/errors/handler-status/analyze', methods=['GET'])
def analyze_error_handlers_route():
    """
    Route handler for error handler analysis
    """
    result = analyze_error_handlers()
    if result.get('success'):
        return jsonify(result), 200
    else:
        return jsonify(result), 500
