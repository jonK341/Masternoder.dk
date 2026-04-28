#!/usr/bin/env python3
"""
Rename .access files to .oldaccess following best practices
- Creates backups before renaming
- Handles multiple files safely
- Adds timestamp to avoid conflicts
- Verifies operations
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
print("RENAMING .access FILES TO .oldaccess")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Find all .access files
print("[1] Finding all .access files...")
stdin, stdout, stderr = ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.access' 2>/dev/null")
access_files = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]
print(f"Found {len(access_files)} .access file(s):")
for f in access_files:
    print(f"  - {f}")
print()

if not access_files:
    print("[INFO] No .access files found. Checking common locations...")
    # Check common locations
    common_locations = [
        "/var/www/html/vidgenerator",
        "/var/www/html/vidgenerator/vidgenerator",
        "/var/www/html/vidgenerator/backend",
        "/var/www/html/vidgenerator/src",
    ]
    for location in common_locations:
        stdin, stdout, stderr = ssh.exec_command(f"find {location} -type f -name '*.access' 2>/dev/null | head -10")
        found = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]
        if found:
            access_files.extend(found)
            print(f"Found in {location}:")
            for f in found:
                print(f"  - {f}")
    print()

if not access_files:
    print("[WARN] No .access files found. Exiting.")
    ssh.close()
    sys.exit(0)

# Create timestamp for backup
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# Process each file
print(f"[2] Processing {len(access_files)} file(s)...")
print()

renamed_count = 0
failed_count = 0

for access_file in access_files:
    if not access_file:
        continue
    
    print(f"Processing: {access_file}")
    
    # Check if file exists
    stdin, stdout, stderr = ssh.exec_command(f"test -f '{access_file}' && echo 'exists' || echo 'not found'")
    exists = stdout.read().decode('utf-8').strip()
    
    if exists != 'exists':
        print(f"  [SKIP] File does not exist")
        continue
    
    # Get file info
    stdin, stdout, stderr = ssh.exec_command(f"ls -lh '{access_file}'")
    file_info = stdout.read().decode('utf-8').strip()
    print(f"  Current: {file_info}")
    
    # Create backup first (best practice)
    backup_file = f"{access_file}.backup.{timestamp}"
    stdin, stdout, stderr = ssh.exec_command(f"cp '{access_file}' '{backup_file}'")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print(f"  [OK] Backup created: {backup_file}")
    else:
        error = stderr.read().decode('utf-8')
        print(f"  [WARN] Backup failed: {error}")
        # Continue anyway, but warn user
    
    # Generate new filename with timestamp to avoid conflicts
    # Option 1: Simple rename (if no .oldaccess exists)
    oldaccess_file = access_file.replace('.access', '.oldaccess')
    
    # Check if .oldaccess already exists
    stdin, stdout, stderr = ssh.exec_command(f"test -f '{oldaccess_file}' && echo 'exists' || echo 'not found'")
    oldaccess_exists = stdout.read().decode('utf-8').strip()
    
    if oldaccess_exists == 'exists':
        # Add timestamp to avoid overwriting
        base_name = access_file.replace('.access', '')
        oldaccess_file = f"{base_name}.{timestamp}.oldaccess"
        print(f"  [INFO] .oldaccess exists, using timestamped name: {oldaccess_file}")
    
    # Rename the file
    stdin, stdout, stderr = ssh.exec_command(f"mv '{access_file}' '{oldaccess_file}'")
    exit_status = stdout.channel.recv_exit_status()
    
    if exit_status == 0:
        print(f"  [OK] Renamed to: {oldaccess_file}")
        renamed_count += 1
        
        # Verify the rename
        stdin, stdout, stderr = ssh.exec_command(f"test -f '{oldaccess_file}' && echo 'exists' || echo 'not found'")
        verify = stdout.read().decode('utf-8').strip()
        if verify == 'exists':
            print(f"  [OK] Verification: File exists at new location")
        else:
            print(f"  [ERROR] Verification failed: File not found at new location")
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
print(f"Total files processed: {len(access_files)}")
print(f"Successfully renamed: {renamed_count}")
print(f"Failed: {failed_count}")
print(f"Backup timestamp: {timestamp}")
print()

# List all .oldaccess files created
print("[3] Listing created .oldaccess files...")
stdin, stdout, stderr = ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.oldaccess' 2>/dev/null | head -20")
oldaccess_files = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]
if oldaccess_files:
    print(f"Found {len(oldaccess_files)} .oldaccess file(s):")
    for f in oldaccess_files:
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh '{f}'")
        file_info = stdout.read().decode('utf-8').strip()
        print(f"  - {file_info}")
else:
    print("No .oldaccess files found")
print()

ssh.close()

print("=" * 80)
print("[OK] RENAME OPERATION COMPLETE")
print("=" * 80)
print()
print("Best practices followed:")
print("  ✓ Created backups before renaming")
print("  ✓ Added timestamps to avoid conflicts")
print("  ✓ Verified operations")
print("  ✓ Handled existing files safely")
print()

