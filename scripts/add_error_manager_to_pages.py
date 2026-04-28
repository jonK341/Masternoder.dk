"""
Add ErrorManager to all HTML pages
Adds the error-manager.js script to all HTML pages in vidgenerator directory
"""
import os
import re
from pathlib import Path


def add_error_manager_to_file(file_path):
    """Add ErrorManager script to an HTML file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        modified = False
        
        # Check if ErrorManager is already included
        if 'error-manager.js' in content:
            return False
        
        # Add ErrorManager script before </body> or before other scripts
        error_manager_script = '<script src="/vidgenerator/static/js/error-manager.js"></script>'
        
        # Try to insert before other scripts (so it loads early)
        script_pattern = r'(<script[^>]*src=["\'][^"\']*\.js[^"\']*["\'][^>]*>)'
        match = re.search(script_pattern, content)
        
        if match:
            # Insert before first script
            insert_pos = match.start()
            content = content[:insert_pos] + f'    {error_manager_script}\n    ' + content[insert_pos:]
            modified = True
        elif '</body>' in content:
            # Insert before </body>
            content = content.replace('</body>', f'    {error_manager_script}\n</body>', 1)
            modified = True
        elif '</html>' in content:
            # Insert before </html>
            content = content.replace('</html>', f'    {error_manager_script}\n</html>', 1)
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
    vidgenerator_dir = Path('vidgenerator')
    
    if not vidgenerator_dir.exists():
        print(f"Error: {vidgenerator_dir} directory not found")
        return
    
    html_files = list(vidgenerator_dir.rglob('*.html'))
    
    print("=" * 70)
    print("ADD ERROR MANAGER TO ALL HTML PAGES")
    print("=" * 70)
    print()
    print(f"Found {len(html_files)} HTML files")
    print()
    
    modified_count = 0
    skipped_count = 0
    
    for html_file in html_files:
        # Skip backup files
        if 'backup' in str(html_file).lower():
            continue
        
        if add_error_manager_to_file(html_file):
            print(f"[OK] Added ErrorManager to {html_file.relative_to(vidgenerator_dir)}")
            modified_count += 1
        else:
            skipped_count += 1
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Modified: {modified_count} files")
    print(f"Skipped: {skipped_count} files (already have ErrorManager or backup files)")
    print()
    print("ErrorManager will now log all errors to the database!")


if __name__ == '__main__':
    main()
