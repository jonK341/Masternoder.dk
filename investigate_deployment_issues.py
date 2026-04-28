#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Investigate Deployment Issues - Check if files are actually updated on server
"""
import paramiko
import os
import sys
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_BASE = "/var/www/html/vidgenerator"

def investigate_deployment():
    """Check deployment status and file contents"""
    print("=" * 80)
    print("INVESTIGATING DEPLOYMENT ISSUES")
    print("=" * 80)
    print()
    
    try:
        # Connect
        print("[1] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("  [OK] Connected")
        print()
        
        # Check index.html file
        print("[2] Checking index.html file...")
        remote_file = f"{REMOTE_BASE}/index.html"
        
        # Check if file exists
        stdin, stdout, stderr = ssh.exec_command(f"test -f {remote_file} && echo 'EXISTS' || echo 'NOT_FOUND'", timeout=10)
        exists = stdout.read().decode('utf-8').strip()
        print(f"  File exists: {exists}")
        
        # Get file size
        stdin, stdout, stderr = ssh.exec_command(f"stat -c%s {remote_file} 2>/dev/null || echo '0'", timeout=10)
        file_size = stdout.read().decode('utf-8').strip()
        print(f"  File size: {file_size} bytes")
        
        # Get file modification time
        stdin, stdout, stderr = ssh.exec_command(f"stat -c%y {remote_file} 2>/dev/null || echo 'UNKNOWN'", timeout=10)
        mod_time = stdout.read().decode('utf-8').strip()
        print(f"  Last modified: {mod_time}")
        
        # Check for update banner
        print()
        print("[3] Checking for update indicators in file...")
        stdin, stdout, stderr = ssh.exec_command(f"grep -c 'Platform Updated' {remote_file} 2>/dev/null || echo '0'", timeout=10)
        banner_count = stdout.read().decode('utf-8').strip()
        print(f"  'Platform Updated' found: {banner_count} times")
        
        stdin, stdout, stderr = ssh.exec_command(f"grep -c 'epic-gaming-experience.js' {remote_file} 2>/dev/null || echo '0'", timeout=10)
        epic_js_count = stdout.read().decode('utf-8').strip()
        print(f"  'epic-gaming-experience.js' found: {epic_js_count} times")
        
        stdin, stdout, stderr = ssh.exec_command(f"grep -c 'comprehensive-loading-fix.js' {remote_file} 2>/dev/null || echo '0'", timeout=10)
        loading_js_count = stdout.read().decode('utf-8').strip()
        print(f"  'comprehensive-loading-fix.js' found: {loading_js_count} times")
        
        stdin, stdout, stderr = ssh.exec_command(f"grep -c 'links-checklist' {remote_file} 2>/dev/null || echo '0'", timeout=10)
        checklist_count = stdout.read().decode('utf-8').strip()
        print(f"  'links-checklist' found: {checklist_count} times")
        
        # Check service status
        print()
        print("[4] Checking service status...")
        services = ['uwsgi', 'python-proxy.service']
        for service in services:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1 || echo 'inactive'", timeout=10)
            status = stdout.read().decode('utf-8').strip()
            print(f"  {service}: {status}")
        
        # Check if there are multiple index.html files
        print()
        print("[5] Checking for multiple index.html files...")
        stdin, stdout, stderr = ssh.exec_command(f"find {REMOTE_BASE} -name 'index.html' -type f 2>/dev/null", timeout=10)
        index_files = stdout.read().decode('utf-8').strip().split('\n')
        index_files = [f for f in index_files if f]
        print(f"  Found {len(index_files)} index.html files:")
        for idx_file in index_files[:10]:  # Show first 10
            stdin, stdout, stderr = ssh.exec_command(f"stat -c%y {idx_file} 2>/dev/null || echo 'UNKNOWN'", timeout=10)
            mod = stdout.read().decode('utf-8').strip()
            print(f"    - {idx_file} (modified: {mod})")
        
        # Check route registration
        print()
        print("[6] Checking if routes are registered...")
        stdin, stdout, stderr = ssh.exec_command(f"grep -c 'comprehensive_fixes_bp' {REMOTE_BASE}/backend/register_blueprints.py 2>/dev/null || echo '0'", timeout=10)
        fixes_reg = stdout.read().decode('utf-8').strip()
        print(f"  comprehensive_fixes_bp references: {fixes_reg}")
        
        stdin, stdout, stderr = ssh.exec_command(f"grep -c 'system_fix_bp' {REMOTE_BASE}/backend/register_blueprints.py 2>/dev/null || echo '0'", timeout=10)
        system_fix_reg = stdout.read().decode('utf-8').strip()
        print(f"  system_fix_bp references: {system_fix_reg}")
        
        print()
        print("=" * 80)
        print("INVESTIGATION COMPLETE")
        print("=" * 80)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Investigation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = investigate_deployment()
    sys.exit(0 if success else 1)
