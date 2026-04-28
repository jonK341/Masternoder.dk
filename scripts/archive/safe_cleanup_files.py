#!/usr/bin/env python3
"""
Safe Cleanup - Only removes clearly unused files
Removes old test scripts and duplicate deployment scripts
"""
import os
from pathlib import Path

# Files to KEEP (never delete)
KEEP_FILES = {
    'deploy.py',
    'src/app.py',
    'wsgi.py',
    'requirements.txt',
    'backend/register_blueprints.py',
    'backend/routes/production_debugger_routes.py',
    'backend/routes/system_aggregator_routes.py',
    'backend/services/production_debugger.py',
    'backend/services/system_aggregator.py',
}

# Patterns for files to DELETE (old test/debug scripts in root)
DELETE_PATTERNS = [
    'check_*.py',  # Old check scripts
    'test_*.py',  # Old test scripts (except tests/ directory)
    'fix_*.py',  # Old fix scripts (except scripts/ directory)
    'verify_*.py',  # Old verify scripts (except scripts/ directory)
    'comprehensive_*.py',  # Old comprehensive scripts
    'complete_*.py',  # Old complete scripts
    'auto_*.py',  # Old auto scripts
    'analyze_*.py',  # Old analyze scripts
    'cleanup_*.py',  # Old cleanup scripts (except scripts/ directory)
]

# Old deployment scripts to remove (keep only deploy.py)
OLD_DEPLOY_SCRIPTS = [
    'deploy_complete_implementation.py',
    'deploy_complete_system.py',
    'comprehensive_redeploy_and_check.py',
    'review_and_redeploy_all.py',
    'deploy_all_non_interactive.py',
    'deploy_full_auto.py',
    'deploy_all_new_systems.py',
    'deploy_all_metal_systems.py',
    'deploy_all_game_features.py',
    'deploy_comprehensive_features_phase2.py',
    'deploy_final_queue.py',
    'deploy_phase3_and_point_connection.py',
]

def should_delete(file_path: str) -> bool:
    """Check if file should be deleted"""
    rel_path = os.path.relpath(file_path, '.')
    
    # Never delete keep files
    if rel_path in KEEP_FILES:
        return False
    
    # Never delete files in important directories
    if any(rel_path.startswith(d) for d in ['backend/', 'src/', 'vidgenerator/', 'scripts/', 'tests/']):
        return False
    
    # Delete old deployment scripts
    filename = os.path.basename(file_path)
    if filename in OLD_DEPLOY_SCRIPTS:
        return True
    
    # Delete files matching patterns (only in root)
    if '/' not in rel_path or rel_path.count('/') == 0:
        for pattern in DELETE_PATTERNS:
            if filename.startswith(pattern.replace('*', '')):
                return True
    
    return False

def main():
    """Main cleanup function"""
    print("="*80)
    print("SAFE CLEANUP - REMOVING OLD SCRIPTS")
    print("="*80)
    print()
    
    files_to_delete = []
    
    # Find files to delete
    for root, dirs, files in os.walk('.'):
        # Skip important directories
        if any(skip in root for skip in ['.git', '__pycache__', 'node_modules', 'venv', 'env', 'backend', 'src', 'vidgenerator', 'scripts', 'tests']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if should_delete(file_path):
                    files_to_delete.append(file_path)
    
    print(f"Found {len(files_to_delete)} files to delete")
    print()
    
    if files_to_delete:
        print("Files to delete:")
        for f in files_to_delete[:30]:
            print(f"  - {f}")
        if len(files_to_delete) > 30:
            print(f"  ... and {len(files_to_delete) - 30} more")
        print()
        
        # Save list
        with open('safe_cleanup_list.txt', 'w', encoding='utf-8') as f:
            for file in files_to_delete:
                f.write(f"{file}\n")
        
        print("Cleanup list saved to safe_cleanup_list.txt")
        print("Review and delete manually if needed")
    else:
        print("No files to delete")

if __name__ == "__main__":
    main()
