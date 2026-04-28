#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Site-Wide Caching Issues
Adds cache-control headers and cache-busting to all HTML pages
"""
import os
import re
import glob
from datetime import datetime

def add_cache_headers_to_html(file_path):
    """Add cache-control meta tags to HTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Check if cache headers already exist
        if '<meta http-equiv="Cache-Control"' in content:
            return False  # Already has cache headers
        
        # Find the head tag
        head_match = re.search(r'(<head[^>]*>)', content, re.IGNORECASE)
        if not head_match:
            return False
        
        # Insert cache headers after head tag
        cache_headers = '''    <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate, max-age=0">
    <meta http-equiv="Pragma" content="no-cache">
    <meta http-equiv="Expires" content="0">
    <meta name="cache-version" content="''' + datetime.now().strftime('%Y%m%d') + '''">'''
        
        insert_pos = head_match.end()
        content = content[:insert_pos] + '\n' + cache_headers + '\n' + content[insert_pos:]
        
        if content != original:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        
        return False
    except Exception as e:
        print(f"  [ERROR] {file_path}: {e}")
        return False

def add_cache_busting_script(file_path):
    """Add JavaScript to force reload main content"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if script already exists
        if 'forceReloadMainContent' in content:
            return False
        
        # Find closing body tag
        body_end = content.rfind('</body>')
        if body_end == -1:
            return False
        
        # Add cache-busting script
        script = '''
    <script>
        // Force reload main content on page load if cache version is old
        (function() {
            const currentVersion = document.querySelector('meta[name="cache-version"]')?.content || '0';
            const storedVersion = sessionStorage.getItem('pageCacheVersion');
            
            if (storedVersion && storedVersion !== currentVersion) {
                // Cache version changed - force reload
                sessionStorage.setItem('pageCacheVersion', currentVersion);
                window.location.reload(true);
            } else if (!storedVersion) {
                // First visit - store version
                sessionStorage.setItem('pageCacheVersion', currentVersion);
            }
            
            // Add cache-busting to all internal links
            document.addEventListener('DOMContentLoaded', function() {
                const links = document.querySelectorAll('a[href^="/vidgenerator/"]');
                links.forEach(link => {
                    if (!link.href.includes('?')) {
                        link.href += '?v=' + currentVersion;
                    }
                });
            });
        })();
    </script>'''
        
        content = content[:body_end] + script + '\n' + content[body_end:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  [ERROR] {file_path}: {e}")
        return False

def fix_all_html_files():
    """Fix caching for all HTML files"""
    print("=" * 70)
    print("FIXING SITE-WIDE CACHING ISSUES")
    print("=" * 70)
    print()
    
    # Find all HTML files
    html_files = []
    for root, dirs, files in os.walk('vidgenerator'):
        # Skip node_modules and other build directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__']]
        
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    print(f"Found {len(html_files)} HTML files")
    print()
    
    fixed_headers = 0
    fixed_scripts = 0
    
    for file_path in html_files:
        rel_path = os.path.relpath(file_path)
        
        if add_cache_headers_to_html(file_path):
            print(f"  [OK] Added cache headers: {rel_path}")
            fixed_headers += 1
        
        if add_cache_busting_script(file_path):
            print(f"  [OK] Added cache-busting script: {rel_path}")
            fixed_scripts += 1
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Files with cache headers added: {fixed_headers}")
    print(f"  Files with cache-busting script: {fixed_scripts}")
    print()
    print("Next: Deploy updated files to server")

if __name__ == '__main__':
    fix_all_html_files()
