#!/usr/bin/env python3
"""
Add Hypnotic Point Counters to All Pages
Automatically injects the hypnotic point counter script into all HTML pages
"""
import os
import re
from pathlib import Path

def find_html_files(directory):
    """Find all HTML files in directory"""
    html_files = []
    for root, dirs, files in os.walk(directory):
        # Skip node_modules and other common directories
        dirs[:] = [d for d in dirs if d not in ['node_modules', '.git', '__pycache__', '.venv']]
        for file in files:
            if file.endswith('.html'):
                html_files.append(os.path.join(root, file))
    return html_files

def add_hypnotic_counter(html_file):
    """Add hypnotic counter script to HTML file if not already present"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already has hypnotic counter
        if 'hypnotic-point-counters.js' in content:
            return False, "Already has hypnotic counter"
        
        # Check if has closing body tag
        if '</body>' not in content:
            return False, "No closing body tag"
        
        # Script tag to inject
        script_tag = '''
    <!-- Hypnotic Point Counters -->
    <script src="/vidgenerator/static/js/hypnotic-point-counters.js"></script>
</body>'''
        
        # Replace closing body tag
        new_content = content.replace('</body>', script_tag)
        
        # Only write if content changed
        if new_content != content:
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True, "Added hypnotic counter"
        
        return False, "No changes needed"
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Main function"""
    vidgenerator_dir = 'vidgenerator'
    
    if not os.path.exists(vidgenerator_dir):
        print(f"❌ Directory {vidgenerator_dir} not found")
        return
    
    print("=" * 80)
    print("Adding Hypnotic Point Counters to All Pages")
    print("=" * 80)
    
    html_files = find_html_files(vidgenerator_dir)
    print(f"Found {len(html_files)} HTML files\n")
    
    added = 0
    skipped = 0
    errors = 0
    
    for html_file in html_files:
        success, message = add_hypnotic_counter(html_file)
        relative_path = os.path.relpath(html_file)
        
        if success:
            print(f"✅ {relative_path} - {message}")
            added += 1
        elif "Already" in message:
            print(f"⏭️  {relative_path} - {message}")
            skipped += 1
        else:
            print(f"⚠️  {relative_path} - {message}")
            errors += 1
    
    print("\n" + "=" * 80)
    print("📊 Summary")
    print("=" * 80)
    print(f"✅ Added: {added}")
    print(f"⏭️  Skipped: {skipped}")
    print(f"⚠️  Errors: {errors}")
    print(f"📄 Total: {len(html_files)}")

if __name__ == '__main__':
    main()

