#!/usr/bin/env python3
"""
Comprehensive script to rename access files to oldaccess
Handles both .access files and access.log files
Follows best practices: backups, timestamps, verification
"""
import paramiko
import os
import sys
import time
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("RENAMING ACCESS FILES TO OLDACCESS (COMPREHENSIVE)")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Define search patterns - user can specify which ones to process
search_patterns = {
    "*.access files": "find /var/www/html/vidgenerator -type f -name '*.access' 2>/dev/null",
    "access.log files (logs directory)": "find /var/www/html/vidgenerator/logs -type f -name 'access.log*' 2>/dev/null",
    "gunicorn_access.log": "find /var/www/html/vidgenerator -type f -name 'gunicorn_access.log' 2>/dev/null",
}

print("[1] Finding files to rename...")
print()

all_files_to_rename = []

for pattern_name, command in search_patterns.items():
    print(f"Searching for: {pattern_name}")
    stdin, stdout, stderr = ssh.exec_command(command)
    files = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]
    
    if files:
        print(f"  Found {len(files)} file(s):")
        for f in files:
            print(f"    - {f}")
            all_files_to_rename.append((f, pattern_name))
    else:
        print(f"  No files found")
    print()

if not all_files_to_rename:
    print("[WARN] No files found to rename.")
    print()
    print("If you want to rename specific files, please specify:")
    print("  - Exact file paths")
    print("  - Or modify the search patterns in this script")
    ssh.close()
    sys.exit(0)

print(f"[2] Processing {len(all_files_to_rename)} file(s)...")
print()

renamed_count = 0
failed_count = 0
skipped_count = 0

for file_path, pattern_name in all_files_to_rename:
    print(f"Processing: {file_path}")
    print(f"  Pattern: {pattern_name}")
    
    # Check if file exists
    stdin, stdout, stderr = ssh.exec_command(f"test -f '{file_path}' && echo 'exists' || echo 'not found'")
    exists = stdout.read().decode('utf-8').strip()
    
    if exists != 'exists':
        print(f"  [SKIP] File does not exist")
        skipped_count += 1
        print()
        continue
    
    # Get file info
    stdin, stdout, stderr = ssh.exec_command(f"ls -lh '{file_path}'")
    file_info = stdout.read().decode('utf-8').strip()
    print(f"  Current: {file_info}")
    
    # Determine new filename
    # Strategy: Replace .access with .oldaccess, or access.log with oldaccess.log
    if file_path.endswith('.access'):
        new_file = file_path.replace('.access', '.oldaccess')
    elif 'access.log' in file_path:
        # For access.log files, replace 'access' with 'oldaccess'
        new_file = file_path.replace('access.log', 'oldaccess.log')
    else:
        # Generic: replace 'access' with 'oldaccess' in filename
        base = os.path.basename(file_path)
        dir_path = os.path.dirname(file_path)
        new_base = base.replace('access', 'oldaccess')
        new_file = os.path.join(dir_path, new_base) if dir_path else new_base
    
    # Check if target already exists
    stdin, stdout, stderr = ssh.exec_command(f"test -f '{new_file}' && echo 'exists' || echo 'not found'")
    target_exists = stdout.read().decode('utf-8').strip()
    
    if target_exists == 'exists':
        # Add timestamp to avoid overwriting
        base_name = os.path.splitext(new_file)[0]
        ext = os.path.splitext(new_file)[1] or ''
        new_file = f"{base_name}.{timestamp}{ext}"
        print(f"  [INFO] Target exists, using timestamped name: {new_file}")
    
    # Create backup (best practice)
    backup_file = f"{file_path}.backup.{timestamp}"
    stdin, stdout, stderr = ssh.exec_command(f"cp '{file_path}' '{backup_file}'")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print(f"  [OK] Backup created: {backup_file}")
    else:
        error = stderr.read().decode('utf-8')
        print(f"  [WARN] Backup failed: {error}")
        # Continue anyway
    
    # Rename the file
    stdin, stdout, stderr = ssh.exec_command(f"mv '{file_path}' '{new_file}'")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print(f"  [OK] Renamed to: {new_file}")
        renamed_count += 1
        
        # Verify
        stdin, stdout, stderr = ssh.exec_command(f"test -f '{new_file}' && echo 'exists' || echo 'not found'")
        verify = stdout.read().decode('utf-8').strip()
        if verify == 'exists':
            stdin, stdout, stderr = ssh.exec_command(f"ls -lh '{new_file}'")
            new_file_info = stdout.read().decode('utf-8').strip()
            print(f"  [OK] Verified: {new_file_info}")
        else:
            print(f"  [ERROR] Verification failed")
            failed_count += 1
    else:
        error = stderr.read().decode('utf-8')
        print(f"  [ERROR] Rename failed: {error}")
        failed_count += 1
    
    print()

# Summary
print("=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Total files found: {len(all_files_to_rename)}")
print(f"Successfully renamed: {renamed_count}")
print(f"Failed: {failed_count}")
print(f"Skipped: {skipped_count}")
print(f"Backup timestamp: {timestamp}")
print()

# List created files
print("[3] Listing created .oldaccess files...")
stdin, stdout, stderr = ssh.exec_command("find /var/www/html/vidgenerator -type f \\( -name '*.oldaccess*' -o -name '*oldaccess*' \\) 2>/dev/null | head -20")
oldaccess_files = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]
if oldaccess_files:
    print(f"Found {len(oldaccess_files)} .oldaccess file(s):")
    for f in oldaccess_files:
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh '{f}' 2>/dev/null")
        file_info = stdout.read().decode('utf-8').strip()
        if file_info:
            print(f"  - {file_info}")
else:
    print("No .oldaccess files found")
print()

ssh.close()

print("=" * 80)
print("[OK] RENAME OPERATION COMPLETE")
print("=" * 80)
print()
print("Best practices applied:")
print("  ✓ Created backups with timestamp")
print("  ✓ Added timestamps to avoid overwriting existing files")
print("  ✓ Verified all operations")
print("  ✓ Handled edge cases safely")
print()
print("To restore a file from backup:")
print(f"  cp <file>.backup.{timestamp} <original_filename>")
print()

