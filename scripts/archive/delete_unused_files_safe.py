#!/usr/bin/env python3
"""
Delete Unused Files Safely
Deletes files from cleanup_list.txt but only if they're safe to delete
"""
import os
from pathlib import Path

# Important directories to NEVER delete files from
PROTECTED_DIRS = {
    'backend',
    'src',
    'vidgenerator',
    'scripts',
    'tests',
    '.git',
    '__pycache__',
    'node_modules',
    'venv',
    'env',
}

# Important files to NEVER delete
PROTECTED_FILES = {
    'deploy.py',
    'wsgi.py',
    'requirements.txt',
    'README.md',
    'backend/register_blueprints.py',
    'src/app.py',
}

def is_safe_to_delete(file_path: str) -> bool:
    """Check if a file is safe to delete"""
    rel_path = os.path.relpath(file_path, '.')
    
    # Never delete protected files
    if rel_path in PROTECTED_FILES:
        return False
    
    # Never delete files in protected directories
    for protected_dir in PROTECTED_DIRS:
        if rel_path.startswith(protected_dir + '/'):
            return False
    
    # Only delete files that exist
    if not os.path.exists(file_path):
        return False
    
    # Only delete .py and .md files (the ones we identified)
    if not (file_path.endswith('.py') or file_path.endswith('.md')):
        return False
    
    return True

def main():
    """Main deletion function"""
    print("="*80)
    print("DELETING UNUSED FILES (SAFE MODE)")
    print("="*80)
    print()
    
    if not os.path.exists('cleanup_list.txt'):
        print("  [ERROR] cleanup_list.txt not found")
        return
    
    # Read files to delete
    with open('cleanup_list.txt', 'r', encoding='utf-8') as f:
        all_files = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"Total files in cleanup list: {len(all_files)}")
    print()
    
    # Filter to safe files only
    safe_files = [f for f in all_files if is_safe_to_delete(f)]
    unsafe_files = [f for f in all_files if not is_safe_to_delete(f)]
    
    print(f"Files safe to delete: {len(safe_files)}")
    print(f"Files protected (skipped): {len(unsafe_files)}")
    print()
    
    if len(safe_files) == 0:
        print("No files are safe to delete (all are protected)")
        return
    
    # Show sample
    print("Sample files to delete (first 20):")
    for f in safe_files[:20]:
        print(f"  - {f}")
    if len(safe_files) > 20:
        print(f"  ... and {len(safe_files) - 20} more")
    print()
    
    # Confirm deletion
    response = input(f"Delete {len(safe_files)} files? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Deletion cancelled")
        return
    
    # Delete files
    print()
    print("Deleting files...")
    deleted = 0
    errors = 0
    
    for file_path in safe_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted += 1
                if deleted % 50 == 0:
                    print(f"  Deleted {deleted}/{len(safe_files)} files...")
        except Exception as e:
            print(f"  [ERROR] {file_path}: {e}")
            errors += 1
    
    print()
    print("="*80)
    print("DELETION COMPLETE")
    print("="*80)
    print(f"Deleted: {deleted} files")
    print(f"Errors: {errors} files")
    print(f"Protected (skipped): {len(unsafe_files)} files")
    print()

if __name__ == "__main__":
    main()
