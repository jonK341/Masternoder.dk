"""
Add Points & Rewards Link to Navigation
Adds points page link to all navigation toolbars across the site
"""
import os
import re
import glob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDGENERATOR_DIR = os.path.join(BASE_DIR, 'vidgenerator')

def find_html_files_with_navigation():
    """Find all HTML files with navigation toolbars"""
    html_files = []
    
    # Search for HTML files
    patterns = [
        'vidgenerator/**/*.html',
        'vidgenerator/**/index.html'
    ]
    
    for pattern in patterns:
        files = glob.glob(os.path.join(BASE_DIR, pattern), recursive=True)
        html_files.extend(files)
    
    # Filter files that have navigation
    files_with_nav = []
    for file_path in html_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'navigation-toolbar' in content or 'nav-container' in content:
                    files_with_nav.append(file_path)
        except:
            pass
    
    return files_with_nav

def add_points_link_to_file(file_path):
    """Add points link to a single file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if points link already exists
        if '/vidgenerator/points' in content or 'Points.*Rewards' in content:
            return False, 'already_exists'
        
        # Find navigation container
        nav_pattern = r'(<div class="nav-container">.*?</div>)'
        match = re.search(nav_pattern, content, re.DOTALL)
        
        if not match:
            return False, 'no_nav_found'
        
        nav_html = match.group(1)
        
        # Check if game link exists (we'll add after it)
        if '/vidgenerator/game' in nav_html:
            # Add points link after game link
            new_nav = re.sub(
                r'(<a href="/vidgenerator/game"[^>]*>.*?</a>)',
                r'\1\n            <a href="/vidgenerator/points" class="nav-item" title="Points & Rewards">💎</a>',
                nav_html,
                flags=re.DOTALL
            )
        elif '/vidgenerator/stats' in nav_html:
            # Add before stats
            new_nav = re.sub(
                r'(<a href="/vidgenerator/stats"[^>]*>)',
                r'<a href="/vidgenerator/points" class="nav-item" title="Points & Rewards">💎</a>\n            \1',
                nav_html
            )
        else:
            # Add at end before closing div
            new_nav = nav_html.replace(
                '</div>',
                '            <a href="/vidgenerator/points" class="nav-item" title="Points & Rewards">💎</a>\n        </div>'
            )
        
        # Replace in content
        new_content = content.replace(nav_html, new_nav)
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return True, 'added'
        
    except Exception as e:
        return False, str(e)

def main():
    """Main function"""
    print("=" * 70)
    print("Adding Points & Rewards Link to Navigation")
    print("=" * 70)
    print()
    
    files = find_html_files_with_navigation()
    print(f"Found {len(files)} files with navigation")
    print()
    
    updated = 0
    skipped = 0
    errors = 0
    
    for file_path in files:
        rel_path = os.path.relpath(file_path, BASE_DIR)
        success, reason = add_points_link_to_file(file_path)
        
        if success:
            print(f"✅ {rel_path}")
            updated += 1
        elif reason == 'already_exists':
            print(f"⏭️  {rel_path} (already has points link)")
            skipped += 1
        elif reason == 'no_nav_found':
            print(f"⚠️  {rel_path} (no navigation found)")
            skipped += 1
        else:
            print(f"❌ {rel_path} (error: {reason})")
            errors += 1
    
    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Updated: {updated}")
    print(f"Skipped: {skipped}")
    print(f"Errors: {errors}")
    print()
    
    if updated > 0:
        print("✅ Points & Rewards link added to navigation!")
    else:
        print("⚠️  No files were updated")

if __name__ == '__main__':
    main()
