#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Integrate navigation toolbar into all HTML pages
"""
import os
import re
import sys

# Fix Unicode encoding on Windows
sys.stdout.reconfigure(encoding='utf-8')

PAGES = [
    'vidgenerator/index.html',
    'vidgenerator/generator/index.html',
    'vidgenerator/gallery/index.html',
    'vidgenerator/game/index.html',
    'vidgenerator/battle/index.html',
    'vidgenerator/stats/index.html',
    'vidgenerator/profile/index.html',
    'vidgenerator/social/index.html',
    'vidgenerator/shop/index.html',
    'vidgenerator/chat/index.html',
    'vidgenerator/debugger/index.html',
    'vidgenerator/analytics/index.html',
]

CSS_LINK = '<link rel="stylesheet" href="/vidgenerator/static/css/navigation-toolbar.css">'
JS_SCRIPT = '<script src="/vidgenerator/static/js/navigation-toolbar.js"></script>'

def integrate_toolbar(file_path):
    """Add navigation toolbar CSS and JS to a page"""
    if not os.path.exists(file_path):
        print(f"[WARN] File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    modified = False
    
    # Add CSS link (after modern-design-system.css or in head)
    if CSS_LINK not in content:
        # Try to find existing CSS links
        css_pattern = r'(<link[^>]*css[^>]*>)'
        matches = list(re.finditer(css_pattern, content, re.IGNORECASE))
        
        if matches:
            # Insert after last CSS link
            last_css = matches[-1]
            insert_pos = last_css.end()
            content = content[:insert_pos] + '\n    ' + CSS_LINK + content[insert_pos:]
            modified = True
        else:
            # Insert in head
            head_pattern = r'(</head>)'
            if re.search(head_pattern, content):
                content = re.sub(head_pattern, f'    {CSS_LINK}\n\\1', content, count=1)
                modified = True
    
    # Add JS script (before </body>)
    if JS_SCRIPT not in content:
        body_pattern = r'(</body>)'
        if re.search(body_pattern, content):
            content = re.sub(body_pattern, f'    {JS_SCRIPT}\n\\1', content, count=1)
            modified = True
    
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Updated: {file_path}")
        return True
    else:
        print(f"[INFO] Already has toolbar: {file_path}")
        return False

def main():
    print("="*80)
    print("INTEGRATING NAVIGATION TOOLBAR INTO ALL PAGES")
    print("="*80)
    print()
    
    updated_count = 0
    for page in PAGES:
        if integrate_toolbar(page):
            updated_count += 1
    
    print()
    print("="*80)
    print(f"COMPLETE: Updated {updated_count}/{len(PAGES)} pages")
    print("="*80)

if __name__ == '__main__':
    main()

