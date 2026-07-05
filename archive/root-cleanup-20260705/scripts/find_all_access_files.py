#!/usr/bin/env python3
"""
Find all access-related files on the server
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("FINDING ALL ACCESS-RELATED FILES")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Search patterns
search_patterns = [
    ("*.access files", "find /var/www/html/vidgenerator -type f -name '*.access' 2>/dev/null"),
    ("access.log files", "find /var/www/html/vidgenerator -type f -name '*access.log*' 2>/dev/null"),
    ("Files with 'access' in name", "find /var/www/html/vidgenerator -type f -name '*access*' 2>/dev/null"),
    ("Apache access logs", "ls -la /var/log/apache2/*access* 2>/dev/null"),
    ("All .access in /var/www", "find /var/www -type f -name '*.access' 2>/dev/null | head -50"),
]

for pattern_name, command in search_patterns:
    print(f"[{pattern_name}]")
    stdin, stdout, stderr = ssh.exec_command(command)
    results = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]
    
    if results:
        print(f"Found {len(results)} file(s):")
        for f in results[:20]:  # Show first 20
            print(f"  - {f}")
        if len(results) > 20:
            print(f"  ... and {len(results) - 20} more")
    else:
        print("  No files found")
    print()

# Also check for files that might need renaming
print("[Checking for files that might need to be renamed...]")
stdin, stdout, stderr = ssh.exec_command("find /var/www/html/vidgenerator -type f \\( -name '*.access' -o -name '*access*' \\) 2>/dev/null | head -50")
all_access = [f.strip() for f in stdout.read().decode('utf-8').split('\n') if f.strip()]

if all_access:
    print(f"Found {len(all_access)} potential file(s) to rename:")
    for f in all_access:
        stdin, stdout, stderr = ssh.exec_command(f"ls -lh '{f}' 2>/dev/null")
        file_info = stdout.read().decode('utf-8').strip()
        if file_info:
            print(f"  - {file_info}")
else:
    print("No files found that match access patterns")
print()

ssh.close()

print("=" * 80)
print("[OK] SEARCH COMPLETE")
print("=" * 80)
print()
print("If you meant Apache access.log files, those are typically in:")
print("  /var/log/apache2/access.log")
print()
print("If you meant .htaccess files, those would be:")
print("  find /var/www/html/vidgenerator -name '.htaccess'")
print()
print("Please specify which files you want renamed to .oldaccess")

