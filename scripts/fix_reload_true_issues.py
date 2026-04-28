#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix window.location.reload(true) Issues
Replaces all instances of reload(true) with safer reload() or removes forced reloads
"""
import os
import re
from pathlib import Path

# Pages we fixed and deployed
FIXED_PAGES = [
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
    'vidgenerator/points/index.html',
    'vidgenerator/stats/index.html',
    'vidgenerator/gallery/index.html',
    'vidgenerator/generator/index.html',
    'vidgenerator/unified_dashboard/index.html',
    'vidgenerator/aggregator/index.html',
]

def fix_reload_true(file_path):
    """Fix window.location.reload(true) in a file"""
    if not os.path.exists(file_path):
        return False, "File not found"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Replace window.location.reload(true) with safer version
        # Pattern 1: Simple reload(true) replacement
        content = re.sub(
            r'window\.location\.reload\(true\)',
            'window.location.reload()',
            content
        )
        
        # Pattern 2: Fix the cache version check pattern that causes loops
        # Replace the problematic pattern that reloads on every check
        problematic_pattern = r'if\s*\(storedVersion\s*&&\s*storedVersion\s*!==\s*currentVersion\)\s*\{[^}]*window\.location\.reload\(\)'
        
        # More specific: Fix the cache version check that reloads immediately
        cache_check_pattern = r'(if\s*\(storedVersion\s*&&\s*storedVersion\s*!==\s*currentVersion\)\s*\{[^\}]*?)(window\.location\.reload\(true?\)|window\.location\.reload\(\))'
        
        def replace_reload(match):
            before = match.group(1)
            # Only reload if not already in a reload loop
            replacement = before + '''sessionStorage.setItem('pageCacheVersion', currentVersion);
                // Only reload once if version changed and not already reloading
                if (window.location.search.indexOf('v=') === -1) {
                    window.location.reload();
                    return;
                }'''
            return replacement
        
        content = re.sub(cache_check_pattern, replace_reload, content, flags=re.DOTALL)
        
        # Also fix the simpler pattern
        simple_pattern = r'window\.location\.reload\(true\)'
        if simple_pattern in content:
            content = re.sub(simple_pattern, 'window.location.reload()', content)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, "Fixed"
        else:
            return True, "No changes needed"
            
    except Exception as e:
        return False, f"Error: {e}"

def main():
    """Main function"""
    print("=" * 80)
    print("FIXING window.location.reload(true) ISSUES")
    print("=" * 80)
    print()
    
    fixed = 0
    failed = 0
    no_change = 0
    
    for file_path in FIXED_PAGES:
        print(f"Fixing {os.path.basename(os.path.dirname(file_path))}/index.html...")
        success, message = fix_reload_true(file_path)
        
        if success:
            if message == "Fixed":
                print(f"  [OK] {message}")
                fixed += 1
            else:
                print(f"  [OK] {message}")
                no_change += 1
        else:
            print(f"  [ERROR] {message}")
            failed += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files Fixed: {fixed}")
    print(f"Files Unchanged: {no_change}")
    print(f"Files Failed: {failed}")
    print()
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
