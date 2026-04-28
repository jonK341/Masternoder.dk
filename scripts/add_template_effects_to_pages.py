"""
Add template effects and services to all HTML pages in vidgenerator directory
"""
import os
import re
from pathlib import Path

def add_template_effects_to_file(file_path):
    """Add template effects CSS and JS to an HTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        
        # Add CSS links in head if not present
        css_files = [
            '<link rel="stylesheet" href="/vidgenerator/static/css/template-effects.css">'
        ]
        
        for css_link in css_files:
            if css_link not in content:
                # Find </head> and insert before it
                if '</head>' in content:
                    content = content.replace('</head>', f'    {css_link}\n</head>', 1)
                    modified = True
        
        # Add JS scripts before </body> if not present
        js_files = [
            '<script src="/vidgenerator/static/js/template-effects.js"></script>',
            '<script src="/vidgenerator/static/js/template-services.js"></script>'
        ]
        
        for js_script in js_files:
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
        if add_template_effects_to_file(html_file):
            print(f"✅ Updated: {html_file.relative_to(vidgenerator_dir.parent)}")
            updated_count += 1
        else:
            print(f"⏭️  Skipped (already has support): {html_file.relative_to(vidgenerator_dir.parent)}")
    
    print(f"\n✅ Updated {updated_count} files with template effects and services")
    print(f"⏭️  Skipped {len(html_files) - updated_count} files (already have support)")

if __name__ == '__main__':
    main()
