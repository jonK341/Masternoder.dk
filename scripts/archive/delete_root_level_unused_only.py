#!/usr/bin/env python3
"""
Delete Root Level Unused Files Only
Only deletes .md and .py files in the root directory, NOT in backend/, src/, etc.
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
    'backup_original',
}

# Important files to NEVER delete
PROTECTED_FILES = {
    'deploy.py',
    'wsgi.py',
    'requirements.txt',
    'README.md',
    'FINAL_DEPLOYMENT_REPORT.md',
    'PRODUCTION_COMPREHENSIVE_REPORT.md',
    'DEPLOYMENT_STATUS_REPORT.md',
    'FIXES_AND_DEPLOYMENT_REPORT.md',
    'TEST_ANALYSIS_AND_CLEANUP_PLAN.md',
    'DEPLOYMENT_PLAN.md',
}

def is_root_level_unused(file_path: str) -> bool:
    """Check if file is in root directory and safe to delete"""
    # Convert to Path for easier handling
    path = Path(file_path)
    
    # Normalize path
    if not path.is_absolute():
        path = Path(os.getcwd()) / path
    
    # Get relative path from current directory
    try:
        rel_path = path.relative_to(os.getcwd())
    except ValueError:
        return False
    
    # Convert backslashes to forward slashes for consistency
    rel_path_str = str(rel_path).replace('\\', '/')
    
    # Never delete protected files
    if rel_path_str in PROTECTED_FILES:
        return False
    
    # Never delete files in protected directories
    parts = rel_path_str.split('/')
    if len(parts) > 0 and parts[0] in PROTECTED_DIRS:
        return False
    
    # Only delete files in root (no subdirectories)
    if '/' in rel_path_str:
        return False
    
    # Only delete .py and .md files
    if not (file_path.endswith('.py') or file_path.endswith('.md')):
        return False
    
    # Only delete files that exist
    if not os.path.exists(file_path):
        return False
    
    return True

def main():
    """Main deletion function"""
    print("="*80)
    print("DELETING ROOT LEVEL UNUSED FILES ONLY")
    print("="*80)
    print()
    print("This will ONLY delete .py and .md files in the ROOT directory.")
    print("Files in backend/, src/, vidgenerator/, scripts/, tests/ will be PROTECTED.")
    print()
    
    if not os.path.exists('cleanup_list.txt'):
        print("  [ERROR] cleanup_list.txt not found")
        return
    
    # Read files to delete
    with open('cleanup_list.txt', 'r', encoding='utf-8') as f:
        all_files = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"Total files in cleanup list: {len(all_files)}")
    print()
    
    # Filter to root-level files only
    root_files = [f for f in all_files if is_root_level_unused(f)]
    protected_files = [f for f in all_files if not is_root_level_unused(f)]
    
    print(f"Root-level files to delete: {len(root_files)}")
    print(f"Protected files (skipped): {len(protected_files)}")
    print()
    
    if len(root_files) == 0:
        print("No root-level files to delete")
        return
    
    # Show sample
    print("Sample files to delete (first 30):")
    for f in root_files[:30]:
        print(f"  - {f}")
    if len(root_files) > 30:
        print(f"  ... and {len(root_files) - 30} more")
    print()
    
    # Delete files
    print("Deleting files...")
    deleted = 0
    errors = 0
    
    for file_path in root_files:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted += 1
                if deleted % 50 == 0:
                    print(f"  Deleted {deleted}/{len(root_files)} files...")
        except Exception as e:
            print(f"  [ERROR] {file_path}: {e}")
            errors += 1
    
    print()
    print("="*80)
    print("DELETION COMPLETE")
    print("="*80)
    print(f"Deleted: {deleted} files")
    print(f"Errors: {errors} files")
    print(f"Protected (skipped): {len(protected_files)} files")
    print()

if __name__ == "__main__":
    main()
