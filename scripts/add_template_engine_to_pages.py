"""
Add template engine core to all HTML pages in vidgenerator directory
"""
import os
import re
from pathlib import Path

def add_template_engine_to_file(file_path):
    """Add template engine core JS to an HTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        
        # Add JS script before </body> if not present
        js_script = '<script src="/vidgenerator/static/js/template-engine-core.js"></script>'
        if js_script not in content:
            # Find </body> and insert before it
            if '</body>' in content:
                content = content.replace('</body>', f'    {js_script}\n</body>', 1)
                modified = True
        
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to process all HTML files"""
    vidgenerator_dir = Path(__file__).parent.parent / 'vidgenerator'
    
    # Find all HTML files
    html_files = list(vidgenerator_dir.rglob('*.html'))
    
    print(f"Found {len(html_files)} HTML files")
    
    updated_count = 0
    for html_file in html_files:
        if add_template_engine_to_file(html_file):
            print(f"✅ Updated: {html_file.relative_to(vidgenerator_dir.parent)}")
            updated_count += 1
        else:
            print(f"⏭️  Skipped (already has support): {html_file.relative_to(vidgenerator_dir.parent)}")
    
    print(f"\n✅ Updated {updated_count} files with template engine core")
    print(f"⏭️  Skipped {len(html_files) - updated_count} files (already have support)")

if __name__ == '__main__':
    main()
