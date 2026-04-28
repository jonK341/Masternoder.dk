#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Detect New Problems
Comprehensive check for new issues after deployment
"""
import os
import re
from pathlib import Path

def check_script_files_exist():
    """Check if all referenced script files actually exist"""
    print("=" * 80)
    print("CHECKING SCRIPT FILES EXIST")
    print("=" * 80)
    print()
    
    issues = []
    
    # Find all HTML files
    html_files = list(Path('vidgenerator').rglob('index.html'))
    
    # Common script paths
    script_pattern = r'src=["\']([^"\']+\.js[^"\']*)["\']'
    
    all_scripts = set()
    missing_scripts = []
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Find all script references
            scripts = re.findall(script_pattern, content)
            
            for script_path in scripts:
                # Skip CDN/external URLs
                if script_path.startswith('http://') or script_path.startswith('https://'):
                    continue
                # Normalize path
                if script_path.startswith('/'):
                    # Absolute path
                    script_file = script_path.lstrip('/')
                elif script_path.startswith('./'):
                    # Relative path
                    script_file = os.path.join(os.path.dirname(html_file), script_path[2:])
                else:
                    # Relative path
                    script_file = os.path.join(os.path.dirname(html_file), script_path)
                
                # Check if file exists
                if not os.path.exists(script_file):
                    # Try with vidgenerator prefix
                    if not script_path.startswith('/vidgenerator/'):
                        alt_path = f'vidgenerator/{script_file}'
                        if not os.path.exists(alt_path):
                            missing_scripts.append({
                                'file': str(html_file),
                                'script': script_path,
                                'expected': script_file
                            })
                else:
                    all_scripts.add(script_path)
        except Exception as e:
            issues.append(f"Error reading {html_file}: {e}")
    
    if missing_scripts:
        print(f"[WARN] Found {len(missing_scripts)} potentially missing scripts:")
        for item in missing_scripts[:10]:  # Show first 10
            print(f"  - {item['file']} references: {item['script']}")
        if len(missing_scripts) > 10:
            print(f"  ... and {len(missing_scripts) - 10} more")
    else:
        print("[OK] All script references appear valid")
    
    print()
    return issues, missing_scripts

def check_plugin_consistency():
    """Check for pages that might still be missing plugins"""
    print("=" * 80)
    print("CHECKING PLUGIN CONSISTENCY")
    print("=" * 80)
    print()
    
    issues = []
    
    # Pages we fixed
    fixed_pages = [
        'profile', 'battle', 'social', 'shop',
        'analytics', 'quests', 'chat', 'debugger',
        'trophies', 'leaderboards', 'monetization',
        'battlegrounds', 'champions-league', 'editor',
        'agent_support', 'beta_testing',
        'points', 'stats', 'gallery', 'generator',
        'unified_dashboard', 'aggregator'
    ]
    
    # Check all HTML files
    html_files = list(Path('vidgenerator').rglob('index.html'))
    
    pages_missing_plugins = []
    
    for html_file in html_files:
        page_name = html_file.parent.name
        
        # Skip if we already fixed it
        if page_name in fixed_pages:
            continue
        
        # Skip main index
        if page_name == 'vidgenerator' or str(html_file) == 'vidgenerator/index.html':
            continue
        
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            has_unified = 'unified-point-counters.js' in content
            has_comprehensive = 'comprehensive-api-integration.js' in content
            
            if not has_unified or not has_comprehensive:
                pages_missing_plugins.append({
                    'page': page_name,
                    'missing_unified': not has_unified,
                    'missing_comprehensive': not has_comprehensive
                })
        except Exception as e:
            issues.append(f"Error reading {html_file}: {e}")
    
    if pages_missing_plugins:
        print(f"[INFO] Found {len(pages_missing_plugins)} pages that might need plugins:")
        for item in pages_missing_plugins[:10]:
            missing = []
            if item['missing_unified']:
                missing.append('unified-point-counters')
            if item['missing_comprehensive']:
                missing.append('comprehensive-api-integration')
            print(f"  - {item['page']}/index.html: Missing {', '.join(missing)}")
        if len(pages_missing_plugins) > 10:
            print(f"  ... and {len(pages_missing_plugins) - 10} more")
    else:
        print("[OK] All checked pages have required plugins")
    
    print()
    return issues, pages_missing_plugins

def check_cache_busting():
    """Check for any remaining aggressive cache-busting"""
    print("=" * 80)
    print("CHECKING FOR AGGRESSIVE CACHE-BUSTING")
    print("=" * 80)
    print()
    
    issues = []
    pages_with_aggressive = []
    
    html_files = list(Path('vidgenerator').rglob('index.html'))
    
    for html_file in html_files:
        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for aggressive patterns
            has_aggressive = False
            problems = []
            
            if 'AGGRESSIVE CACHE-BUSTING' in content:
                has_aggressive = True
                problems.append('AGGRESSIVE CACHE-BUSTING comment')
            
            # Flag reload(true) - causes refresh loops (legitimate setInterval for data refresh is OK)
            if 'reload(true)' in content:
                has_aggressive = True
                problems.append('reload(true)')
            
            if 'Intercept fetch/XHR' in content and 'url.searchParams.set' in content:
                has_aggressive = True
                problems.append('Fetch interception with timestamps')
            
            if has_aggressive:
                pages_with_aggressive.append({
                    'page': html_file.parent.name,
                    'problems': problems
                })
        except Exception as e:
            issues.append(f"Error reading {html_file}: {e}")
    
    if pages_with_aggressive:
        print(f"[WARN] Found {len(pages_with_aggressive)} pages with aggressive cache-busting:")
        for item in pages_with_aggressive[:10]:
            print(f"  - {item['page']}/index.html: {', '.join(item['problems'])}")
        if len(pages_with_aggressive) > 10:
            print(f"  ... and {len(pages_with_aggressive) - 10} more")
    else:
        print("[OK] No aggressive cache-busting found")
    
    print()
    return issues, pages_with_aggressive

def check_database_issues():
    """Check for potential database issues"""
    print("=" * 80)
    print("CHECKING FOR DATABASE ISSUES")
    print("=" * 80)
    print()
    
    issues = []
    
    # Check if migration scripts exist
    migration_scripts = [
        'scripts/unified_points_database_migration.py',
        'scripts/update_all_point_tables.py',
    ]
    
    missing_scripts = []
    for script in migration_scripts:
        if not os.path.exists(script):
            missing_scripts.append(script)
    
    if missing_scripts:
        print(f"[WARN] Missing migration scripts: {', '.join(missing_scripts)}")
    else:
        print("[OK] All migration scripts exist")
    
    print()
    return issues

def main():
    """Main problem detection"""
    print("=" * 80)
    print("DETECTING NEW PROBLEMS")
    print("=" * 80)
    print()
    
    all_issues = []
    all_warnings = []
    
    # 1. Check script files
    issues, missing_scripts = check_script_files_exist()
    all_issues.extend(issues)
    if missing_scripts:
        all_warnings.append(f"{len(missing_scripts)} potentially missing script files")
    
    # 2. Check plugin consistency
    issues, missing_plugins = check_plugin_consistency()
    all_issues.extend(issues)
    if missing_plugins:
        all_warnings.append(f"{len(missing_plugins)} pages might need plugins")
    
    # 3. Check cache-busting
    issues, aggressive_pages = check_cache_busting()
    all_issues.extend(issues)
    if aggressive_pages:
        all_warnings.append(f"{len(aggressive_pages)} pages with aggressive cache-busting")
    
    # 4. Check database
    issues = check_database_issues()
    all_issues.extend(issues)
    
    # Summary
    print("=" * 80)
    print("PROBLEM DETECTION SUMMARY")
    print("=" * 80)
    print()
    
    if all_issues:
        print(f"[ERROR] Found {len(all_issues)} errors:")
        for issue in all_issues[:10]:
            print(f"  - {issue}")
        if len(all_issues) > 10:
            print(f"  ... and {len(all_issues) - 10} more")
        print()
    
    if all_warnings:
        print(f"[WARN] Found {len(all_warnings)} potential issues:")
        for warning in all_warnings:
            print(f"  - {warning}")
        print()
    
    if not all_issues and not all_warnings:
        print("[OK] No new problems detected!")
        print()
        print("All systems appear to be working correctly.")
    else:
        print("Review the issues above for potential problems.")
    
    print()
    return len(all_issues) == 0 and len(all_warnings) == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
