#!/usr/bin/env python3
"""
Delete Root Level Markdown and Old Python Scripts
Deletes .md files and old .py scripts from root directory only
"""
import os
from pathlib import Path

# Files to NEVER delete
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
    'CLEANUP_AND_VERIFICATION_REPORT.md',
    'FINAL_CLEANUP_AND_VERIFICATION_SUMMARY.md',
    'FINAL_CLEANUP_AND_FIXES_REPORT.md',
}

def find_root_level_files():
    """Find .md and .py files in root directory"""
    root_dir = Path('.')
    files_to_delete = []
    
    # Find .md files
    for md_file in root_dir.glob('*.md'):
        if md_file.name not in PROTECTED_FILES:
            files_to_delete.append(str(md_file))
    
    # Find .py files (old scripts)
    patterns_to_delete = [
        'check_*.py',
        'test_*.py',
        'fix_*.py',
        'verify_*.py',
        'comprehensive_*.py',
        'complete_*.py',
        'auto_*.py',
        'analyze_*.py',
        'cleanup_*.py',
        'audit_*.py',
        'batch_*.py',
        'append_*.py',
        'capture_*.py',
        'clear_*.py',
        'configure_*.py',
        'delete_*.py',
    ]
    
    for py_file in root_dir.glob('*.py'):
        if py_file.name not in PROTECTED_FILES:
            # Check if matches any delete pattern
            for pattern in patterns_to_delete:
                pattern_prefix = pattern.replace('*.py', '')
                if py_file.name.startswith(pattern_prefix):
                    files_to_delete.append(str(py_file))
                    break
    
    return files_to_delete

def main():
    """Main deletion function"""
    print("="*80)
    print("DELETING ROOT LEVEL MARKDOWN AND OLD SCRIPTS")
    print("="*80)
    print()
    print("This will delete .md and .py files from the ROOT directory only.")
    print("Protected files will be skipped.")
    print()
    
    files_to_delete = find_root_level_files()
    
    if not files_to_delete:
        print("No files found to delete")
        return
    
    print(f"Found {len(files_to_delete)} files to delete")
    print()
    
    # Show sample
    print("Sample files to delete (first 30):")
    for f in files_to_delete[:30]:
        print(f"  - {os.path.basename(f)}")
    if len(files_to_delete) > 30:
        print(f"  ... and {len(files_to_delete) - 30} more")
    print()
    
    # Delete files
    print("Deleting files...")
    deleted = 0
    errors = 0
    
    for file_path in files_to_delete:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted += 1
                if deleted % 50 == 0:
                    print(f"  Deleted {deleted}/{len(files_to_delete)} files...")
        except Exception as e:
            print(f"  [ERROR] {file_path}: {e}")
            errors += 1
    
    print()
    print("="*80)
    print("DELETION COMPLETE")
    print("="*80)
    print(f"Deleted: {deleted} files")
    print(f"Errors: {errors} files")
    print()

if __name__ == "__main__":
    main()
