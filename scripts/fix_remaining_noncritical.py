#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix All Remaining Non-Critical Issues
1. Add missing plugins (unified-point-counters, comprehensive-api-integration) to 13 pages
2. Remove aggressive cache-busting (Force reload + AGGRESSIVE block) and replace with simple check
"""
import os
import re

SIMPLE_CACHE_SCRIPT = '''    <script>
        // Simple cache version check (no aggressive reloading)
        (function() {
            const currentVersion = document.querySelector('meta[name="cache-version"]')?.content || document.querySelector('meta[name="version"]')?.content || '0';
            const storedVersion = sessionStorage.getItem('pageCacheVersion');
            if (storedVersion && storedVersion !== currentVersion && storedVersion !== '0') {
                sessionStorage.setItem('pageCacheVersion', currentVersion);
                if (window.location.search.indexOf('v=') === -1) { window.location.reload(); return; }
            }
            if (!storedVersion) sessionStorage.setItem('pageCacheVersion', currentVersion);
        })();
    </script>'''

# Force reload block pattern (multi-line) - match through </script>
FORCE_RELOAD_BLOCK = re.compile(
    r'<script>\s*//\s*Force reload main content on page load if cache version is old\s*'
    r'\(function\(\) \{\s*const currentVersion.*?</script>',
    re.DOTALL
)

# AGGRESSIVE CACHE-BUSTING block - from "// AGGRESSIVE" to closing </script>
AGGRESSIVE_BLOCK = re.compile(
    r'<script>\s*//\s*AGGRESSIVE CACHE-BUSTING FOR MAIN CONTENT\s*'
    r'\(function\(\) \{.*?\}\)\(\);\s*</script>',
    re.DOTALL
)

PAGES = [
    ('vidgenerator/danish-divine-tech-tree/index.html', True, True),   # add both plugins
    ('vidgenerator/dashboard/index.html', False, True),   # add comprehensive only
    ('vidgenerator/game/index.html', False, True),
    ('vidgenerator/metal/index.html', True, True),
    ('vidgenerator/milkyway/index.html', True, True),
    ('vidgenerator/rights-law/index.html', True, True),
    ('vidgenerator/theme-points/index.html', True, True),
    ('vidgenerator/theme_premium/index.html', True, True),
    ('vidgenerator/victory-tech-tree/index.html', True, True),
    ('vidgenerator/time-achievement-guides/index.html', True, True),
    ('vidgenerator/index.html', True, True),
]

FEATURE_SCRIPTS = {
    (True, True): '\n    <!-- Feature Scripts (load after template system) -->\n    <script src="/vidgenerator/static/js/unified-point-counters.js"></script>\n    <script src="/vidgenerator/static/js/comprehensive-api-integration.js"></script>',
    (False, True): '\n    <!-- Feature Scripts (load after template system) -->\n    <script src="/vidgenerator/static/js/comprehensive-api-integration.js"></script>',
}


def add_plugins(content, add_unified, add_comprehensive):
    """Add missing plugins after template-engine-core."""
    if not add_unified and not add_comprehensive:
        return content
    # Avoid adding if already present
    if add_comprehensive and 'comprehensive-api-integration.js' in content:
        return content
    if add_unified and 'unified-point-counters.js' in content and add_comprehensive:
        return content
    insertion = FEATURE_SCRIPTS[(add_unified, add_comprehensive)]
    pattern = r'(<script\s+src="/vidgenerator/static/js/template-engine-core\.js[^"]*"></script>)'
    match = re.search(pattern, content)
    if not match:
        return content
    insert_pos = match.end()
    return content[:insert_pos] + insertion + content[insert_pos:]


def remove_force_reload(content):
    """Remove Force reload script block."""
    return FORCE_RELOAD_BLOCK.sub('', content)


def remove_aggressive(content):
    """Remove AGGRESSIVE CACHE-BUSTING script block."""
    return AGGRESSIVE_BLOCK.sub('', content)


def ensure_simple_cache(content):
    """Ensure simple cache script exists; add if no cache script left."""
    if 'Simple cache version check' in content or 'pageCacheVersion' not in content:
        return content
    # We removed force reload + aggressive; add simple once. Run after removals.
    return content


def fix_file(path, add_unified, add_comprehensive):
    if not os.path.exists(path):
        return False, f"Not found: {path}"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content

    # 1. Add plugins
    content = add_plugins(content, add_unified, add_comprehensive)

    # 2. Remove Force reload block
    content = remove_force_reload(content)

    # 3. Remove AGGRESSIVE block
    content = remove_aggressive(content)

    # 4. Add simple cache script if we removed blocks and no simple one exists
    if 'Simple cache version check' not in content and ('Force reload' in orig or 'AGGRESSIVE CACHE-BUSTING' in orig):
        pos = content.rfind('</body>')
        if pos != -1:
            content = content[:pos] + '\n' + SIMPLE_CACHE_SCRIPT + '\n' + content[pos:]

    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, "Fixed"
    return True, "No changes"


def main():
    print("Fixing remaining non-critical issues...")
    for path, add_u, add_c in PAGES:
        ok, msg = fix_file(path, add_u, add_c)
        print(f"  {path}: {msg}")
    print("Done.")


if __name__ == '__main__':
    main()
