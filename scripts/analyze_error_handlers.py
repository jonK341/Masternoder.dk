#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze Error Handlers Status
Counts and categorizes all error handlers in the codebase
"""
import os
import re
from pathlib import Path
from collections import defaultdict

def analyze_error_handlers():
    """Analyze all error handlers in the codebase"""
    print("=" * 70)
    print("ERROR HANDLERS STATUS ANALYSIS")
    print("=" * 70)
    print()
    
    js_dir = Path('vidgenerator/static/js')
    if not js_dir.exists():
        print("Error: vidgenerator/static/js directory not found")
        return
    
    error_patterns = {
        'console.error': r'console\.error',
        'console.warn': r'console\.warn',
        'catch_blocks': r'catch\s*\([^)]*\)',
        'promise_catch': r'\.catch\s*\(',
        'try_blocks': r'try\s*\{',
        'error_handlers': r'(error|Error|ERROR)',
    }
    
    stats = {
        'files_analyzed': 0,
        'total_files': 0,
        'error_handlers_by_file': {},
        'error_handlers_by_type': defaultdict(int),
        'files_with_error_manager': [],
        'files_without_error_manager': [],
    }
    
    js_files = list(js_dir.glob('*.js'))
    stats['total_files'] = len(js_files)
    
    print(f"Analyzing {len(js_files)} JavaScript files...")
    print()
    
    for js_file in js_files:
        stats['files_analyzed'] += 1
        try:
            with open(js_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            file_stats = {}
            has_error_manager = 'ErrorManager' in content or 'error-manager' in content
            
            for pattern_name, pattern in error_patterns.items():
                matches = len(re.findall(pattern, content, re.IGNORECASE))
                file_stats[pattern_name] = matches
                stats['error_handlers_by_type'][pattern_name] += matches
            
            total_handlers = sum(file_stats.values())
            file_stats['total'] = total_handlers
            
            if total_handlers > 0:
                stats['error_handlers_by_file'][js_file.name] = file_stats
            
            if has_error_manager:
                stats['files_with_error_manager'].append(js_file.name)
            elif total_handlers > 0:
                stats['files_without_error_manager'].append(js_file.name)
                
        except Exception as e:
            print(f"  [ERROR] Could not analyze {js_file.name}: {e}")
    
    # Print summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    print(f"Total JavaScript files: {stats['total_files']}")
    print(f"Files analyzed: {stats['files_analyzed']}")
    print(f"Files with error handlers: {len(stats['error_handlers_by_file'])}")
    print(f"Files using ErrorManager: {len(stats['files_with_error_manager'])}")
    print(f"Files without ErrorManager: {len(stats['files_without_error_manager'])}")
    print()
    
    print("Error Handlers by Type:")
    for handler_type, count in sorted(stats['error_handlers_by_type'].items(), key=lambda x: x[1], reverse=True):
        print(f"  {handler_type}: {count}")
    print()
    
    print("Top 10 Files with Most Error Handlers:")
    sorted_files = sorted(stats['error_handlers_by_file'].items(), 
                         key=lambda x: x[1].get('total', 0), reverse=True)[:10]
    for filename, file_stats in sorted_files:
        print(f"  {filename}: {file_stats.get('total', 0)} handlers")
    print()
    
    # Save to JSON for use in debugger
    import json
    output_file = 'error_handlers_status.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, default=str)
    
    print(f"Status saved to: {output_file}")
    print()
    
    return stats

if __name__ == '__main__':
    analyze_error_handlers()
