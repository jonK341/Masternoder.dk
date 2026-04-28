#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Plugin Additions - Hard Test All URLs
Verifies that all plugins were correctly added to all pages
"""
import os
import re
from pathlib import Path

# Pages that should have both plugins
PAGES_WITH_BOTH_PLUGINS = [
    'vidgenerator/profile/index.html',
    'vidgenerator/battle/index.html',
    'vidgenerator/social/index.html',
    'vidgenerator/shop/index.html',
    'vidgenerator/analytics/index.html',
    'vidgenerator/quests/index.html',
    'vidgenerator/chat/index.html',
    'vidgenerator/debugger/index.html',
    'vidgenerator/trophies/index.html',
    'vidgenerator/leaderboards/index.html',
    'vidgenerator/monetization/index.html',
    'vidgenerator/battlegrounds/index.html',
    'vidgenerator/champions-league/index.html',
    'vidgenerator/editor/index.html',
    'vidgenerator/agent_support/index.html',
    'vidgenerator/beta_testing/index.html',
]

# Pages that should have comprehensive-api-integration (already have unified-point-counters)
PAGES_WITH_COMPREHENSIVE_API = [
    'vidgenerator/points/index.html',
    'vidgenerator/stats/index.html',
    'vidgenerator/gallery/index.html',
    'vidgenerator/generator/index.html',
    'vidgenerator/unified_dashboard/index.html',
    'vidgenerator/aggregator/index.html',
]

def verify_plugin_urls(file_path):
    """Verify plugin script URLs are correct"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for correct URL format
        script_pattern = r'<script\s+src=["\']([^"\']+unified-point-counters\.js[^"\']*)["\']'
        matches = re.findall(script_pattern, content)
        
        for match in matches:
            if not match.startswith('/vidgenerator/static/js/'):
                issues.append(f"Invalid URL format for unified-point-counters: {match}")
        
        script_pattern = r'<script\s+src=["\']([^"\']+comprehensive-api-integration\.js[^"\']*)["\']'
        matches = re.findall(script_pattern, content)
        
        for match in matches:
            if not match.startswith('/vidgenerator/static/js/'):
                issues.append(f"Invalid URL format for comprehensive-api-integration: {match}")
        
        return issues
        
    except Exception as e:
        return [f"Error reading file: {e}"]

def verify_plugins_present(file_path, should_have_both=True):
    """Verify plugins are present in file"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        has_unified = 'unified-point-counters.js' in content
        has_comprehensive = 'comprehensive-api-integration.js' in content
        
        if should_have_both:
            if not has_unified:
                issues.append("Missing: unified-point-counters.js")
            if not has_comprehensive:
                issues.append("Missing: comprehensive-api-integration.js")
        else:
            if not has_comprehensive:
                issues.append("Missing: comprehensive-api-integration.js")
        
        # Check for aggressive cache-busting
        if 'AGGRESSIVE CACHE-BUSTING' in content:
            issues.append("WARNING: Aggressive cache-busting script found (may cause refresh loops)")
        
        if 'Intercept fetch/XHR' in content and 'setInterval' in content:
            # Check if it's the problematic pattern
            if 'url.searchParams.set(\'_\', Date.now())' in content:
                issues.append("WARNING: Fetch interception with timestamps found (may cause loops)")
        
        return issues
        
    except Exception as e:
        return [f"Error reading file: {e}"]

def verify_script_order(file_path):
    """Verify scripts are in correct loading order"""
    issues = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract script tags in order
        script_pattern = r'<script\s+src=["\']([^"\']+)["\']'
        scripts = re.findall(script_pattern, content)
        
        # Check order: error-manager should come first, then core, then features
        error_manager_idx = None
        unified_idx = None
        comprehensive_idx = None
        template_core_idx = None
        
        for i, script in enumerate(scripts):
            if 'error-manager.js' in script:
                error_manager_idx = i
            if 'unified-point-counters.js' in script:
                unified_idx = i
            if 'comprehensive-api-integration.js' in script:
                comprehensive_idx = i
            if 'template-engine-core.js' in script:
                template_core_idx = i
        
        if error_manager_idx is not None:
            if unified_idx is not None and unified_idx < error_manager_idx:
                issues.append("WARNING: unified-point-counters loaded before error-manager")
            if comprehensive_idx is not None and comprehensive_idx < error_manager_idx:
                issues.append("WARNING: comprehensive-api-integration loaded before error-manager")
        
        if template_core_idx is not None and unified_idx is not None:
            if unified_idx < template_core_idx:
                issues.append("WARNING: unified-point-counters loaded before template-engine-core")
        
        return issues
        
    except Exception as e:
        return [f"Error checking script order: {e}"]

def main():
    """Main verification function"""
    print("=" * 80)
    print("VERIFYING PLUGIN ADDITIONS - HARD TEST")
    print("=" * 80)
    print()
    
    all_issues = {}
    all_passed = True
    
    # Verify pages with both plugins
    print("[1/3] Verifying pages with both plugins (16 pages)...")
    for file_path in PAGES_WITH_BOTH_PLUGINS:
        if not os.path.exists(file_path):
            print(f"  [ERROR] {file_path} - FILE NOT FOUND")
            all_issues[file_path] = ["File not found"]
            all_passed = False
            continue
        
        issues = []
        issues.extend(verify_plugins_present(file_path, should_have_both=True))
        issues.extend(verify_plugin_urls(file_path))
        issues.extend(verify_script_order(file_path))
        
        if issues:
            all_issues[file_path] = issues
            all_passed = False
            print(f"  [FAIL] {os.path.basename(os.path.dirname(file_path))}/index.html")
            for issue in issues:
                print(f"         - {issue}")
        else:
            print(f"  [OK] {os.path.basename(os.path.dirname(file_path))}/index.html")
    
    print()
    
    # Verify pages with comprehensive-api-integration
    print("[2/3] Verifying pages with comprehensive-api-integration (6 pages)...")
    for file_path in PAGES_WITH_COMPREHENSIVE_API:
        if not os.path.exists(file_path):
            print(f"  [ERROR] {file_path} - FILE NOT FOUND")
            all_issues[file_path] = ["File not found"]
            all_passed = False
            continue
        
        issues = []
        issues.extend(verify_plugins_present(file_path, should_have_both=False))
        issues.extend(verify_plugin_urls(file_path))
        issues.extend(verify_script_order(file_path))
        
        if issues:
            all_issues[file_path] = issues
            all_passed = False
            print(f"  [FAIL] {os.path.basename(os.path.dirname(file_path))}/index.html")
            for issue in issues:
                print(f"         - {issue}")
        else:
            print(f"  [OK] {os.path.basename(os.path.dirname(file_path))}/index.html")
    
    print()
    
    # Summary
    print("[3/3] Summary...")
    print()
    print("=" * 80)
    print("VERIFICATION RESULTS")
    print("=" * 80)
    print()
    
    total_pages = len(PAGES_WITH_BOTH_PLUGINS) + len(PAGES_WITH_COMPREHENSIVE_API)
    pages_with_issues = len(all_issues)
    pages_passed = total_pages - pages_with_issues
    
    print(f"Total Pages Checked: {total_pages}")
    print(f"Pages Passed: {pages_passed}")
    print(f"Pages With Issues: {pages_with_issues}")
    print()
    
    if all_issues:
        print("ISSUES FOUND:")
        for file_path, issues in all_issues.items():
            print(f"  {file_path}:")
            for issue in issues:
                print(f"    - {issue}")
        print()
    
    if all_passed:
        print("[SUCCESS] All plugins verified correctly!")
        print()
        print("All pages have:")
        print("  - Correct plugin URLs (/vidgenerator/static/js/...)")
        print("  - Proper script loading order")
        print("  - No aggressive cache-busting")
        print("  - All required plugins present")
    else:
        print("[WARNING] Some issues found - see above for details")
    
    print()
    return all_passed

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
