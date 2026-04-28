#!/usr/bin/env python3
"""
Cleanup Unused Files
Identifies and removes unused .py and .md files
"""
import os
import re
from pathlib import Path
from typing import Set, List

# Core files that should NEVER be deleted
CORE_FILES = {
    'src/app.py',
    'wsgi.py',
    'deploy.py',
    'requirements.txt',
    'backend/register_blueprints.py',
}

# Directories to keep
KEEP_DIRECTORIES = {
    'backend',
    'src',
    'vidgenerator',
    'scripts',
    'tests',
}

def get_referenced_files() -> Set[str]:
    """Get all files referenced in core application files"""
    referenced = set()
    
    # Check deploy.py
    if os.path.exists('deploy.py'):
        with open('deploy.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract file paths from deploy.py
            matches = re.findall(r'["\']([^"\']+\.(py|html|js|css))["\']', content)
            referenced.update([m[0] for m in matches])
    
    # Check register_blueprints.py
    if os.path.exists('backend/register_blueprints.py'):
        with open('backend/register_blueprints.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract imports
            matches = re.findall(r'from\s+backend\.(routes|services)\.(\w+)', content)
            referenced.update([f'backend/{m[0]}/{m[1]}.py' for m in matches])
    
    # Check src/app.py
    if os.path.exists('src/app.py'):
        with open('src/app.py', 'r', encoding='utf-8') as f:
            content = f.read()
            matches = re.findall(r'from\s+([\w.]+)\s+import', content)
            for match in matches:
                if match.startswith('backend.') or match.startswith('src.'):
                    parts = match.split('.')
                    if len(parts) >= 2:
                        referenced.add(f"{parts[0]}/{parts[1]}.py")
    
    return referenced

def find_unused_py_files() -> List[str]:
    """Find unused .py files"""
    referenced = get_referenced_files()
    unused = []
    
    # Find all .py files
    for root, dirs, files in os.walk('.'):
        # Skip certain directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', 'venv', 'env']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, '.')
                
                # Skip core files
                if rel_path in CORE_FILES:
                    continue
                
                # Skip if in keep directories
                if any(rel_path.startswith(keep) for keep in KEEP_DIRECTORIES):
                    # Check if referenced
                    if rel_path not in referenced and not rel_path.startswith('scripts/'):
                        # Check if it's a standalone script (has if __name__ == "__main__")
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                if '__main__' in content or 'if __name__' in content:
                                    # It's a script, might be used
                                    continue
                        except:
                            pass
                        
                        unused.append(rel_path)
    
    return unused

def find_unused_md_files() -> List[str]:
    """Find unused .md files - keep only recent/important ones"""
    important_md = {
        'README.md',
        'FINAL_DEPLOYMENT_REPORT.md',
        'PRODUCTION_COMPREHENSIVE_REPORT.md',
        'DEPLOYMENT_STATUS_REPORT.md',
        'FIXES_AND_DEPLOYMENT_REPORT.md',
        'TEST_ANALYSIS_AND_CLEANUP_PLAN.md',
        'DEPLOYMENT_PLAN.md',
    }
    
    unused = []
    
    for root, dirs, files in os.walk('.'):
        if any(skip in root for skip in ['.git', 'node_modules', 'venv', 'env', 'tests']):
            continue
        
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, '.')
                
                # Keep important files
                if file in important_md or rel_path.startswith('tests/'):
                    continue
                
                # Check if it's a recent report (contains "2026" or "2025")
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()[:500]  # First 500 chars
                        if '2026' in content or '2025' in content:
                            # Recent file, might be important
                            continue
                except:
                    pass
                
                unused.append(rel_path)
    
    return unused

def main():
    """Main cleanup function"""
    print("="*80)
    print("CLEANING UP UNUSED FILES")
    print("="*80)
    print()
    
    # Find unused files
    print("[1/3] Finding unused .py files...")
    unused_py = find_unused_py_files()
    print(f"  Found {len(unused_py)} unused .py files")
    
    print()
    print("[2/3] Finding unused .md files...")
    unused_md = find_unused_md_files()
    print(f"  Found {len(unused_md)} unused .md files")
    
    print()
    print("[3/3] Summary:")
    print(f"  Unused .py files: {len(unused_py)}")
    print(f"  Unused .md files: {len(unused_md)}")
    print()
    
    # Show first 20 of each
    if unused_py:
        print("Sample unused .py files (first 20):")
        for f in unused_py[:20]:
            print(f"  - {f}")
        if len(unused_py) > 20:
            print(f"  ... and {len(unused_py) - 20} more")
        print()
    
    if unused_md:
        print("Sample unused .md files (first 20):")
        for f in unused_md[:20]:
            print(f"  - {f}")
        if len(unused_md) > 20:
            print(f"  ... and {len(unused_md) - 20} more")
        print()
    
    # Ask for confirmation (for safety, we'll just list them)
    print("="*80)
    print("FILES TO DELETE (saved to cleanup_list.txt)")
    print("="*80)
    
    with open('cleanup_list.txt', 'w', encoding='utf-8') as f:
        f.write("# Unused .py files\n")
        for file in unused_py:
            f.write(f"{file}\n")
        f.write("\n# Unused .md files\n")
        for file in unused_md:
            f.write(f"{file}\n")
    
    print(f"Cleanup list saved to cleanup_list.txt")
    print(f"Total files to delete: {len(unused_py) + len(unused_md)}")
    print()
    print("Review cleanup_list.txt and delete manually if needed")

if __name__ == "__main__":
    main()
