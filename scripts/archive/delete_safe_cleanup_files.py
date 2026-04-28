#!/usr/bin/env python3
"""
Delete Safe Cleanup Files
Deletes files from safe_cleanup_list.txt
"""
import os

def delete_files():
    """Delete files from safe cleanup list"""
    print("="*80)
    print("DELETING SAFE CLEANUP FILES")
    print("="*80)
    print()
    
    if not os.path.exists('safe_cleanup_list.txt'):
        print("  [ERROR] safe_cleanup_list.txt not found")
        return
    
    with open('safe_cleanup_list.txt', 'r', encoding='utf-8') as f:
        files_to_delete = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print(f"Found {len(files_to_delete)} files to delete")
    print()
    
    deleted = 0
    errors = 0
    
    for file_path in files_to_delete:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"  [DELETED] {file_path}")
                deleted += 1
            except Exception as e:
                print(f"  [ERROR] {file_path}: {e}")
                errors += 1
        else:
            print(f"  [SKIP] {file_path} (not found)")
    
    print()
    print("="*80)
    print("CLEANUP COMPLETE")
    print("="*80)
    print(f"Deleted: {deleted} files")
    print(f"Errors: {errors} files")
    print()

if __name__ == "__main__":
    delete_files()
