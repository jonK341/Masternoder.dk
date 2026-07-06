#!/usr/bin/env python3
"""
Update All UI Index Files with Enhanced Point Counting Layers
Adds intelligent middleware and enhanced accountability to all pages
"""
import os
import re
from pathlib import Path

def find_html_files(directory):
    """Find all HTML files"""
    html_files = []
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.venv']]
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    return html_files

def add_enhanced_counters(html_file):
    """Add enhanced point counting scripts to HTML file"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        scripts_to_add = []
        
        # Check and add intelligent middleware frontend
        if 'intelligent_point_middleware_frontend.js' not in content:
            scripts_to_add.append('<script src="/vidgenerator/static/js/intelligent_point_middleware_frontend.js"></script>')
        
        # Check and add hypnotic counters (if not already present)
        if 'hypnotic-point-counters.js' not in content:
            scripts_to_add.append('<script src="/vidgenerator/static/js/hypnotic-point-counters.js"></script>')
        
        # Check and add unified counters (if not already present)
        if 'unified-point-counters.js' not in content:
            scripts_to_add.append('<script src="/vidgenerator/static/js/unified-point-counters.js"></script>')
        
        if not scripts_to_add:
            return False, "Already has all enhanced counters"
        
        if '</body>' not in content:
            return False, "No closing body tag"
        
        # Add initialization script
        init_script = '''
    <!-- Enhanced Point Counting Layers -->
    <script>
        // Initialize intelligent middleware on page load
        if (window.intelligentPointMiddlewareFrontend) {
            // Sync with backend on load
            window.intelligentPointMiddlewareFrontend.syncWithBackend('default')
                .then(data => {
                    console.log('[Enhanced Counters] Synced with backend:', data);
                })
                .catch(err => {
                    console.warn('[Enhanced Counters] Sync failed:', err);
                });
            
            // Auto-sync every 30 seconds
            setInterval(() => {
                window.intelligentPointMiddlewareFrontend.syncWithBackend('default')
                    .catch(err => console.warn('[Enhanced Counters] Auto-sync failed:', err));
            }, 30000);
        }
    </script>
</body>'''
        
        # Replace closing body tag
        new_content = content.replace('</body>', '\n'.join(scripts_to_add) + init_script)
        
        if new_content != content:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, f"Added {len(scripts_to_add)} enhanced counter scripts"
        
        return False, "No changes needed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Main function"""
    vidgenerator_dir = 'vidgenerator'
    
    if not os.path.exists(vidgenerator_dir):
        print(f"Directory {vidgenerator_dir} not found")
        return
    
    print("=" * 80)
    print("Updating All UI Files with Enhanced Point Counting Layers")
    print("=" * 80)
    
    html_files = find_html_files(vidgenerator_dir)
    print(f"Found {len(html_files)} HTML files\n")
    
    added = 0
    skipped = 0
    errors = 0
    
    for html_file in html_files:
        success, message = add_enhanced_counters(html_file)
        relative_path = os.path.relpath(html_file)
        
        if success:
            print(f"OK {relative_path} - {message}")
            added += 1
        elif "Already" in message:
            print(f"SKIP {relative_path} - {message}")
            skipped += 1
        else:
            print(f"WARN {relative_path} - {message}")
            errors += 1
    
    print("\n" + "=" * 80)
    print("Summary")
    print("=" * 80)
    print(f"Added: {added}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print(f"Total: {len(html_files)}")

if __name__ == '__main__':
    main()

