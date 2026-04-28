#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Content Refresh - Add aggressive content refresh to all pages
Adds JavaScript that forces main content area to refresh
"""
import os
import re

def add_content_refresh_script(file_path):
    """Add aggressive content refresh script"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has aggressive refresh
        if 'AGGRESSIVE CACHE-BUSTING FOR MAIN CONTENT' in content:
            return False
        
        # Find closing body tag
        body_end = content.rfind('</body>')
        if body_end == -1:
            return False
        
        # Add aggressive refresh script
        script = '''
    <script>
        // AGGRESSIVE CACHE-BUSTING FOR MAIN CONTENT
        (function() {
            const currentVersion = document.querySelector('meta[name="cache-version"]')?.content || Date.now().toString();
            const storedVersion = sessionStorage.getItem('pageCacheVersion');
            const contentVersion = sessionStorage.getItem('contentCacheVersion');
            
            // Force reload if version changed
            if (storedVersion && storedVersion !== currentVersion) {
                sessionStorage.clear();
                sessionStorage.setItem('pageCacheVersion', currentVersion);
                sessionStorage.setItem('contentCacheVersion', currentVersion);
                window.location.href = window.location.href.split('?')[0] + '?v=' + currentVersion + '&_=' + Date.now();
                return;
            }
            
            // Store versions
            sessionStorage.setItem('pageCacheVersion', currentVersion);
            if (!contentVersion || contentVersion !== currentVersion) {
                sessionStorage.setItem('contentCacheVersion', currentVersion);
            }
            
            // Force reload main content area on every load
            function forceReloadContent() {
                const mainContent = document.querySelector('.container') || document.querySelector('main') || document.querySelector('#main') || document.body;
                if (mainContent) {
                    // Add timestamp to force re-render
                    mainContent.setAttribute('data-version', currentVersion);
                    mainContent.setAttribute('data-timestamp', Date.now());
                    
                    // Force style recalculation
                    const display = window.getComputedStyle(mainContent).display;
                    mainContent.style.display = 'none';
                    mainContent.offsetHeight; // Trigger reflow
                    mainContent.style.display = display;
                    
                    // Add comment to force HTML change detection
                    const comment = document.createComment(' FORCED REFRESH ' + Date.now() + ' ');
                    mainContent.insertBefore(comment, mainContent.firstChild);
                }
            }
            
            // Run immediately and on DOM ready
            forceReloadContent();
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', forceReloadContent);
            } else {
                setTimeout(forceReloadContent, 100);
            }
            
            // Add cache-busting to all links and forms
            function addCacheBusting() {
                const links = document.querySelectorAll('a[href^="/vidgenerator/"], a[href^="/"]');
                links.forEach(link => {
                    const url = new URL(link.href, window.location.origin);
                    if (!url.searchParams.has('v')) {
                        url.searchParams.set('v', currentVersion);
                        url.searchParams.set('_', Date.now());
                        link.href = url.toString();
                    }
                });
                
                // Add to forms
                const forms = document.querySelectorAll('form[action]');
                forms.forEach(form => {
                    const action = form.getAttribute('action');
                    if (action && !action.includes('v=')) {
                        const separator = action.includes('?') ? '&' : '?';
                        form.setAttribute('action', action + separator + 'v=' + currentVersion + '&_=' + Date.now());
                    }
                });
            }
            
            // Run on DOM ready and periodically
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', addCacheBusting);
            } else {
                addCacheBusting();
            }
            
            // Periodic check for content updates
            setInterval(function() {
                const stored = sessionStorage.getItem('contentCacheVersion');
                if (stored && stored !== currentVersion) {
                    window.location.reload(true);
                }
            }, 5000);
            
            // Intercept fetch/XHR to add cache-busting
            const originalFetch = window.fetch;
            window.fetch = function(...args) {
                if (typeof args[0] === 'string' && args[0].startsWith('/')) {
                    const url = new URL(args[0], window.location.origin);
                    url.searchParams.set('_', Date.now());
                    args[0] = url.toString();
                }
                return originalFetch.apply(this, args);
            };
        })();
    </script>'''
        
        content = content[:body_end] + script + '\n' + content[body_end:]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  [ERROR] {file_path}: {e}")
        return False

def process_all_html():
    """Process all HTML files"""
    print("=" * 70)
    print("ADDING AGGRESSIVE CONTENT REFRESH")
    print("=" * 70)
    print()
    
    html_files = []
    for root, dirs, files in os.walk('vidgenerator'):
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__']]
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    
    print(f"Found {len(html_files)} HTML files")
    print()
    
    updated = 0
    for file_path in html_files:
        if add_content_refresh_script(file_path):
            print(f"  [OK] {os.path.relpath(file_path)}")
            updated += 1
    
    print()
    print(f"Updated {updated} files")
    print("Next: Deploy to server")

if __name__ == '__main__':
    process_all_html()
