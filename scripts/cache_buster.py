#!/usr/bin/env python3
"""
Cache Buster Script
Adds version timestamps to static file references in HTML files
Forces browser to reload CSS/JS files after deployment
"""
import os
import re
from datetime import datetime

def add_cache_buster_to_html(html_file_path, version=None):
    """
    Add cache-busting query parameters to static file references in HTML
    
    Args:
        html_file_path: Path to HTML file
        version: Version string (defaults to timestamp)
    """
    if not os.path.exists(html_file_path):
        print(f"[WARN] File not found: {html_file_path}")
        return False
    
    if version is None:
        version = datetime.now().strftime("%Y%m%d%H%M%S")
    
    with open(html_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern to match static file references (CSS and JS)
    # Matches: href="/path/to/file.css" or src="/path/to/file.js"
    # First, remove existing query parameters to avoid duplicates
    content = re.sub(r'(\?v=[\d]+)+', '', content)
    
    patterns = [
        # CSS files - match href="/vidgenerator/static/css/file.css"
        (r'(href=["\']/vidgenerator/static/css/([^"\']+\.css))(["\'"])', r'\1?v=' + version + r'\3'),
        # JS files - match src="/vidgenerator/static/js/file.js"
        (r'(src=["\']/vidgenerator/static/js/([^"\']+\.js))(["\'"])', r'\1?v=' + version + r'\3'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Also add meta tags for cache control
    if '<meta name="cache-version"' not in content:
        cache_meta = f'    <meta name="cache-version" content="{version}">\n'
        # Insert after charset meta tag
        content = re.sub(
            r'(<meta charset="[^"]+">)',
            r'\1\n' + cache_meta,
            content,
            count=1
        )
    
    if content != original_content:
        with open(html_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[OK] Updated {html_file_path} with cache version {version}")
        return True
    else:
        print(f"[INFO] No changes needed for {html_file_path}")
        return False

def main():
    """Main function to process all HTML files"""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    html_files = [
        os.path.join(base_dir, 'vidgenerator', 'unified_dashboard', 'index.html'),
        os.path.join(base_dir, 'vidgenerator', 'dashboard', 'index.html'),
        os.path.join(base_dir, 'vidgenerator', 'aggregator', 'index.html'),
        os.path.join(base_dir, 'vidgenerator', 'analytics', 'index.html'),
        os.path.join(base_dir, 'vidgenerator', 'admin', 'analytics.html'),
        os.path.join(base_dir, 'vidgenerator', 'leaderboards', 'index.html'),
        os.path.join(base_dir, 'vidgenerator', 'index.html'),
    ]
    
    version = datetime.now().strftime("%Y%m%d%H%M%S")
    print(f"Cache busting with version: {version}\n")
    
    updated_count = 0
    for html_file in html_files:
        if add_cache_buster_to_html(html_file, version):
            updated_count += 1
    
    print(f"\n[OK] Updated {updated_count} file(s)")
    print(f"Version: {version}")
    print("\nTip: Deploy files and hard refresh browser (Ctrl+F5)")

if __name__ == '__main__':
    main()
