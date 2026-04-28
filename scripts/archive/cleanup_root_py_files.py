#!/usr/bin/env python3
"""
Cleanup Root Directory Python Files
Removes unused/finished .py files from root directory
Based on analysis showing 213 deployment scripts and other unused files
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Set

# Essential scripts to NEVER remove
ESSENTIAL_SCRIPTS = {
    'deploy.py',
    'wsgi.py',
    'run.py',
}

# Scripts to keep (might have different functionality)
KEEP_SCRIPTS = {
    'deploy.sh',
    'deploy.bat',
    'deploy.ps1',
}

def get_root_py_files() -> List[Path]:
    """Get all .py files in root directory"""
    root = Path('.')
    py_files = []
    
    for file in root.iterdir():
        if not file.is_file():
            continue
        if not file.name.endswith('.py'):
            continue
        if file.name.startswith('.'):
            continue
        py_files.append(file)
    
    return sorted(py_files)

def categorize_files(files: List[Path]) -> dict:
    """Categorize files for removal"""
    categorized = {
        'keep_essential': [],
        'keep_others': [],
        'remove_deployment': [],
        'remove_one_time': [],
        'remove_other': [],
    }
    
    # Patterns for files to remove
    deployment_patterns = ['deploy_', 'copy_']
    one_time_patterns = ['final_', 'comprehensive_', 'complete_', 'all_']
    fix_patterns = ['fix_', 'debug_', 'diagnose_', 'check_', 'test_', 'verify_']
    other_patterns = ['add_', 'create_', 'find_', 'remove_', 'get_', 'enable_', 'disable_', 
                     'emergency_', 'hard_', 'force_', 'restart_', 'start_', 'setup_', 
                     'generate_', 'update_', 'implement_', 'integrate_', 'investigate_',
                     'query_', 'quick_', 'read_', 'rename_', 'retest_', 'run_', 'scan_',
                     'set_', 'simple_', 'ui_', 'unlock_']
    
    for file_path in files:
        filename = file_path.name
        
        # Essential scripts - keep
        if filename in ESSENTIAL_SCRIPTS:
            categorized['keep_essential'].append(file_path)
            continue
        
        # Keep scripts (might have different functionality)
        if filename in KEEP_SCRIPTS:
            categorized['keep_others'].append(file_path)
            continue
        
        # Deployment scripts - remove (duplicates of deploy.py)
        if any(filename.startswith(pattern) for pattern in deployment_patterns):
            categorized['remove_deployment'].append(file_path)
            continue
        
        # One-time fix/comprehensive scripts - remove
        if any(filename.startswith(pattern) for pattern in one_time_patterns):
            categorized['remove_one_time'].append(file_path)
            continue
        
        # Other utility scripts - remove (should be in scripts/ directory)
        if any(filename.startswith(pattern) for pattern in other_patterns):
            categorized['remove_other'].append(file_path)
            continue
        
        # Unknown files - keep for now
        categorized['keep_others'].append(file_path)
    
    return categorized

def create_backup_directory() -> Path:
    """Create backup directory for removed scripts"""
    backup_base = Path('removed_scripts_backup')
    backup_base.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = backup_base / timestamp
    backup_dir.mkdir(exist_ok=True)
    return backup_dir

def main():
    """Main cleanup function"""
    print("="*80)
    print("ROOT DIRECTORY PYTHON FILES CLEANUP")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get all .py files in root
    print("Scanning root directory for .py files...")
    py_files = get_root_py_files()
    
    print(f"Found {len(py_files)} Python files in root directory\n")
    
    if not py_files:
        print("No Python files found in root directory.")
        return
    
    # Categorize files
    categorized = categorize_files(py_files)
    
    # Count files to remove
    files_to_remove = (
        categorized['remove_deployment'] +
        categorized['remove_one_time'] +
        categorized['remove_other']
    )
    
    # Display summary
    print("File Categorization:")
    print(f"  Essential (keep): {len(categorized['keep_essential'])}")
    print(f"  Other (keep): {len(categorized['keep_others'])}")
    print(f"  Deployment scripts (remove): {len(categorized['remove_deployment'])}")
    print(f"  One-time scripts (remove): {len(categorized['remove_one_time'])}")
    print(f"  Other utility scripts (remove): {len(categorized['remove_other'])}")
    print(f"\n  Total to remove: {len(files_to_remove)}")
    print()
    
    # Show essential files
    if categorized['keep_essential']:
        print("Essential files (keeping):")
        for file in categorized['keep_essential']:
            print(f"  ✓ {file.name}")
        print()
    
    # Show files to remove
    if files_to_remove:
        print("Files to remove:")
        for file in files_to_remove[:50]:
            print(f"  - {file.name}")
        if len(files_to_remove) > 50:
            print(f"  ... and {len(files_to_remove) - 50} more")
        print()
    
    # Show files to keep (other)
    if categorized['keep_others']:
        print("Other files (keeping for review):")
        for file in categorized['keep_others'][:20]:
            print(f"  ? {file.name}")
        if len(categorized['keep_others']) > 20:
            print(f"  ... and {len(categorized['keep_others']) - 20} more")
        print()
    
    # Ask for confirmation
    print("="*80)
    print("ACTION REQUIRED")
    print("="*80)
    print("\nThis script will:")
    print("  1. Create backup directory: removed_scripts_backup/YYYYMMDD_HHMMSS/")
    print("  2. Move {} files to backup (not delete)".format(len(files_to_remove)))
    print("  3. Generate cleanup report")
    print("\nNOTE: Files are MOVED to backup, not deleted permanently.")
    print("      You can restore them later if needed.\n")
    
    if not files_to_remove:
        print("No files to remove. Cleanup complete.")
        return
    
    response = input(f"Move {len(files_to_remove)} files to backup? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Cleanup cancelled.")
        return
    
    # Create backup directory
    backup_dir = create_backup_directory()
    print(f"\nBackup directory: {backup_dir}\n")
    
    # Move files to backup
    moved_files = []
    failed_files = []
    
    print("Moving files to backup...")
    for file_path in files_to_remove:
        try:
            backup_path = backup_dir / file_path.name
            
            # Move file
            shutil.move(str(file_path), str(backup_path))
            moved_files.append(file_path.name)
            if len(moved_files) <= 10:
                print(f"  [OK] Moved: {file_path.name}")
        except Exception as e:
            failed_files.append((file_path.name, str(e)))
            print(f"  [ERROR] Failed to move {file_path.name}: {e}")
    
    if len(moved_files) > 10:
        print(f"  ... moved {len(moved_files)} files total")
    
    print(f"\nMoved {len(moved_files)} files to backup")
    if failed_files:
        print(f"Failed to move {len(failed_files)} files")
    
    # Generate report
    report_file = backup_dir / 'cleanup_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("ROOT DIRECTORY PYTHON FILES CLEANUP REPORT\n")
        f.write("="*80 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Backup Directory: {backup_dir}\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total files moved: {len(moved_files)}\n\n")
        
        if categorized['remove_deployment']:
            f.write("Deployment scripts removed ({}):\n".format(len(categorized['remove_deployment'])))
            for file in categorized['remove_deployment']:
                if file.name in moved_files:
                    f.write(f"  - {file.name}\n")
            f.write("\n")
        
        if categorized['remove_one_time']:
            f.write("One-time scripts removed ({}):\n".format(len(categorized['remove_one_time'])))
            for file in categorized['remove_one_time']:
                if file.name in moved_files:
                    f.write(f"  - {file.name}\n")
            f.write("\n")
        
        if categorized['remove_other']:
            f.write("Other utility scripts removed ({}):\n".format(len(categorized['remove_other'])))
            for file in categorized['remove_other']:
                if file.name in moved_files:
                    f.write(f"  - {file.name}\n")
            f.write("\n")
        
        if failed_files:
            f.write("Files that failed to move:\n")
            for filename, error in failed_files:
                f.write(f"  - {filename}: {error}\n")
            f.write("\n")
        
        f.write("Files kept:\n")
        f.write(f"  Essential: {len(categorized['keep_essential'])}\n")
        for file in categorized['keep_essential']:
            f.write(f"    - {file.name}\n")
        f.write(f"  Other: {len(categorized['keep_others'])}\n")
        for file in categorized['keep_others'][:50]:
            f.write(f"    - {file.name}\n")
        if len(categorized['keep_others']) > 50:
            f.write(f"    ... and {len(categorized['keep_others']) - 50} more\n")
    
    print(f"\nReport saved to: {report_file}")
    print("\n" + "="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print(f"\nMoved {len(moved_files)} files to backup directory:")
    print(f"  {backup_dir}")
    print(f"\nRemaining Python files in root: {len(py_files) - len(moved_files)}")
    print("\nTo restore a file:")
    print(f"  cp {backup_dir}/filename.py .")

if __name__ == "__main__":
    main()
