#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix All Plugin Issues - Remove aggressive cache-busting and fix script order
"""
import os
import re
from pathlib import Path

# All pages that need fixes
PAGES_TO_FIX = [
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

def remove_aggressive_cache_busting(content):
    """Remove aggressive cache-busting script"""
    # Find the start of aggressive cache-busting
    start_pattern = r'<script>\s*//\s*AGGRESSIVE CACHE-BUSTING FOR MAIN CONTENT'
    start_match = re.search(start_pattern, content)
    
    if not start_match:
        return content
    
    # Find the end of the script block (look for closing </script> after the function)
    # The aggressive script ends with });\s*</script>
    # We need to find the matching </script> after the function closes
    start_pos = start_match.start()
    
    # Look for the pattern: });\s*</script> after the start
    # Count opening and closing braces to find the end
    remaining = content[start_pos:]
    brace_count = 0
    in_function = False
    end_pos = -1
    
    for i, char in enumerate(remaining):
        if char == '(' and remaining[i-10:i].strip().endswith('function'):
            in_function = True
            brace_count = 1
        elif in_function:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found end of function, look for </script>
                    script_end = remaining[i:].find('</script>')
                    if script_end != -1:
                        end_pos = start_pos + i + script_end + 9
                        break
    
    if end_pos == -1:
        # Fallback: find </script> after AGGRESSIVE CACHE-BUSTING
        script_end = content[start_pos:].find('</script>', 500)
        if script_end != -1:
            end_pos = start_pos + script_end + 9
    
    if end_pos > start_pos:
        # Replace the entire block
        replacement = '''<script>
        // Simple cache version check (no aggressive reloading)
        (function() {
            const currentVersion = document.querySelector('meta[name="cache-version"]')?.content || document.querySelector('meta[name="version"]')?.content || '0';
            const storedVersion = sessionStorage.getItem('pageCacheVersion');
            
            // Only reload if version actually changed (not on every load)
            if (storedVersion && storedVersion !== currentVersion && storedVersion !== '0') {
                sessionStorage.setItem('pageCacheVersion', currentVersion);
                // Only reload once if version changed
                if (window.location.search.indexOf('v=') === -1) {
                    window.location.reload();
                    return;
                }
            }
            
            // Store version only once
            if (!storedVersion) {
                sessionStorage.setItem('pageCacheVersion', currentVersion);
            }
        })();
    </script>'''
        content = content[:start_pos] + replacement + content[end_pos:]
    
    return content

def fix_script_order(content):
    """Fix script loading order - move unified-point-counters and comprehensive-api-integration after template-engine-core"""
    # Find unified-point-counters and comprehensive-api-integration script tags
    unified_pattern = r'<script\s+src=["\']/vidgenerator/static/js/unified-point-counters\.js[^"\']*["\']></script>'
    comprehensive_pattern = r'<script\s+src=["\']/vidgenerator/static/js/comprehensive-api-integration\.js[^"\']*["\']></script>'
    
    unified_match = re.search(unified_pattern, content)
    comprehensive_match = re.search(comprehensive_pattern, content)
    template_core_match = re.search(r'<script\s+src=["\']/vidgenerator/static/js/template-engine-core\.js[^"\']*["\']></script>', content)
    
    if unified_match and comprehensive_match and template_core_match:
        unified_script = unified_match.group(0)
        comprehensive_script = comprehensive_match.group(0)
        template_core_script = template_core_match.group(0)
        
        # Get positions
        unified_pos = unified_match.start()
        comprehensive_pos = comprehensive_match.start()
        template_core_pos = template_core_match.start()
        
        # If unified or comprehensive come before template-core, move them after
        if unified_pos < template_core_pos or comprehensive_pos < template_core_pos:
            # Remove the scripts from their current positions
            content = content.replace(unified_script, '', 1)
            content = content.replace(comprehensive_script, '', 1)
            
            # Find template-core position again after removal
            template_core_match = re.search(r'<script\s+src=["\']/vidgenerator/static/js/template-engine-core\.js[^"\']*["\']></script>', content)
            if template_core_match:
                insert_pos = template_core_match.end()
                # Insert after template-core
                feature_scripts = f'\n    <!-- Feature Scripts (load after template system) -->\n    {unified_script}\n    {comprehensive_script}'
                content = content[:insert_pos] + feature_scripts + content[insert_pos:]
    
    return content

def fix_file(file_path):
    """Fix a single file"""
    if not os.path.exists(file_path):
        return False, f"File not found: {file_path}"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Remove aggressive cache-busting
        if 'AGGRESSIVE CACHE-BUSTING' in content:
            content = remove_aggressive_cache_busting(content)
        
        # Fix script order
        content = fix_script_order(content)
        
        # Only write if changed
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
    print("FIXING ALL PLUGIN ISSUES")
    print("=" * 80)
    print()
    
    fixed = 0
    failed = 0
    
    for file_path in PAGES_TO_FIX:
        print(f"Fixing {os.path.basename(os.path.dirname(file_path))}/index.html...")
        success, message = fix_file(file_path)
        
        if success:
            print(f"  [OK] {message}")
            fixed += 1
        else:
            print(f"  [ERROR] {message}")
            failed += 1
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Files Fixed: {fixed}")
    print(f"Files Failed: {failed}")
    print()
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
