#!/usr/bin/env python3
"""
Cleanup Root-Level Deployment Scripts
Identifies and safely removes duplicate deployment scripts from root directory
Based on analysis that found 229 candidates for removal
"""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import List, Set

# Scripts to ALWAYS KEEP (never delete)
ESSENTIAL_SCRIPTS = {
    'deploy.py',
    'wsgi.py',
    'run.py',
    'deploy.sh',
    'deploy.bat',
    'deploy.ps1',
}

# Scripts that might have different functionality (review first)
REVIEW_BEFORE_REMOVING = {
    'deploy_automatic.py',
    'copy_server.py',
    'copy_server_fast.py',
    'copy_static_only.py',
}

# Patterns for deployment scripts to remove
DEPLOYMENT_PATTERNS = [
    'deploy_',
    'copy_',
    'final_',
    'comprehensive_',
]

def get_root_deployment_scripts() -> List[str]:
    """Get all deployment scripts in root directory"""
    root = Path('.')
    scripts = []
    
    for file in root.iterdir():
        if not file.is_file():
            continue
        
        if not file.name.endswith('.py'):
            continue
        
        # Skip essential scripts
        if file.name in ESSENTIAL_SCRIPTS:
            continue
        
        # Check if matches deployment pattern
        for pattern in DEPLOYMENT_PATTERNS:
            if file.name.startswith(pattern):
                scripts.append(str(file))
                break
    
    return sorted(scripts)

def categorize_scripts(scripts: List[str]) -> dict:
    """Categorize scripts for removal"""
    categorized = {
        'safe_to_remove': [],
        'review_first': [],
        'keep': [],
    }
    
    for script_path in scripts:
        script_name = Path(script_path).name
        
        # Check if it's a review candidate
        if script_name in REVIEW_BEFORE_REMOVING:
            categorized['review_first'].append(script_path)
            continue
        
        # Most deployment scripts are safe to remove
        categorized['safe_to_remove'].append(script_path)
    
    return categorized

def create_backup_directory():
    """Create backup directory for removed scripts"""
    backup_dir = Path('removed_scripts_backup')
    backup_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamp_dir = backup_dir / timestamp
    timestamp_dir.mkdir(exist_ok=True)
    return timestamp_dir

def main():
    """Main cleanup function"""
    print("="*80)
    print("ROOT-LEVEL DEPLOYMENT SCRIPTS CLEANUP")
    print("="*80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Get all deployment scripts
    print("Scanning root directory for deployment scripts...")
    scripts = get_root_deployment_scripts()
    
    print(f"Found {len(scripts)} deployment scripts in root directory\n")
    
    if not scripts:
        print("No deployment scripts found to clean up.")
        return
    
    # Categorize scripts
    categorized = categorize_scripts(scripts)
    
    print("Categorization:")
    print(f"  Safe to remove: {len(categorized['safe_to_remove'])}")
    print(f"  Review first: {len(categorized['review_first'])}")
    print(f"  Keep: {len(categorized['keep'])}\n")
    
    # Show scripts to remove
    if categorized['safe_to_remove']:
        print("Scripts safe to remove ({}):".format(len(categorized['safe_to_remove'])))
        for script in categorized['safe_to_remove'][:30]:
            print(f"  - {script}")
        if len(categorized['safe_to_remove']) > 30:
            print(f"  ... and {len(categorized['safe_to_remove']) - 30} more")
        print()
    
    # Show scripts to review
    if categorized['review_first']:
        print("Scripts to review first ({}):".format(len(categorized['review_first'])))
        for script in categorized['review_first']:
            print(f"  - {script}")
        print()
    
    # Ask for confirmation
    print("="*80)
    print("ACTIONS")
    print("="*80)
    print("\nThis script will:")
    print("  1. Create a backup directory: removed_scripts_backup/")
    print("  2. Move scripts to backup (not delete)")
    print("  3. Generate a report of removed scripts")
    print("\nNOTE: Scripts are MOVED to backup, not deleted permanently.")
    print("      You can restore them later if needed.\n")
    
    response = input(f"Move {len(categorized['safe_to_remove'])} scripts to backup? (yes/no): ").strip().lower()
    
    if response not in ['yes', 'y']:
        print("Cleanup cancelled.")
        return
    
    # Create backup directory
    backup_dir = create_backup_directory()
    print(f"\nBackup directory: {backup_dir}\n")
    
    # Move scripts to backup
    moved_scripts = []
    failed_scripts = []
    
    print("Moving scripts to backup...")
    for script_path in categorized['safe_to_remove']:
        try:
            script_file = Path(script_path)
            backup_path = backup_dir / script_file.name
            
            # Move file
            shutil.move(str(script_file), str(backup_path))
            moved_scripts.append(script_path)
            print(f"  [OK] Moved: {script_file.name}")
        except Exception as e:
            failed_scripts.append((script_path, str(e)))
            print(f"  [ERROR] Failed to move {script_path}: {e}")
    
    print(f"\nMoved {len(moved_scripts)} scripts to backup")
    if failed_scripts:
        print(f"Failed to move {len(failed_scripts)} scripts")
    
    # Generate report
    report_file = backup_dir / 'cleanup_report.txt'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("="*80 + "\n")
        f.write("ROOT-LEVEL DEPLOYMENT SCRIPTS CLEANUP REPORT\n")
        f.write("="*80 + "\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Backup Directory: {backup_dir}\n")
        f.write("="*80 + "\n\n")
        
        f.write(f"Total scripts moved: {len(moved_scripts)}\n\n")
        f.write("Scripts moved to backup:\n")
        for script in moved_scripts:
            f.write(f"  - {script}\n")
        
        if failed_scripts:
            f.write("\nScripts that failed to move:\n")
            for script, error in failed_scripts:
                f.write(f"  - {script}: {error}\n")
        
        if categorized['review_first']:
            f.write("\nScripts to review before removing:\n")
            for script in categorized['review_first']:
                f.write(f"  - {script}\n")
    
    print(f"\nReport saved to: {report_file}")
    print("\n" + "="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print(f"\nMoved {len(moved_scripts)} scripts to backup directory:")
    print(f"  {backup_dir}")
    print("\nTo restore a script:")
    print(f"  cp {backup_dir}/script_name.py .")

if __name__ == "__main__":
    main()
