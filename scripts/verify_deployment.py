#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify Deployment - Check what's actually on server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_APP_ROOT = "/var/www/html/vidgenerator"

def verify():
    """Verify what's on server"""
    ssh = None
    try:
        print("=" * 70)
        print("VERIFYING DEPLOYMENT")
        print("=" * 70)
        print()
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Check debugger file
        print("Checking debugger/index.html...")
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -c 'cache-version' {REMOTE_APP_ROOT}/vidgenerator/debugger/index.html 2>&1",
            timeout=10
        )
        count = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"  cache-version references: {count}")
        
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -c 'Cache-Control' {REMOTE_APP_ROOT}/vidgenerator/debugger/index.html 2>&1",
            timeout=10
        )
        count = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"  Cache-Control references: {count}")
        
        stdin, stdout, stderr = ssh.exec_command(
            f"grep -c 'AGGRESSIVE CACHE-BUSTING\\|pageCacheVersion' {REMOTE_APP_ROOT}/vidgenerator/debugger/index.html 2>&1",
            timeout=10
        )
        count = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"  Cache-busting script: {count}")
        print()
        
        # Check nginx config
        print("Checking nginx config...")
        stdin, stdout, stderr = ssh.exec_command(
            "grep -c 'location ~ \\\\.html' /etc/nginx/sites-available/default 2>&1",
            timeout=10
        )
        count = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"  HTML no-cache rule: {count}")
        print()
        
        # Check service status
        print("Service status:")
        for service in ['python-proxy', 'nginx', 'uwsgi-vidgenerator']:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode('utf-8', errors='ignore').strip()
            print(f"  {service}: {status}")
        print()
        
        # Get file modification time
        print("File modification times:")
        stdin, stdout, stderr = ssh.exec_command(
            f"stat -c '%y' {REMOTE_APP_ROOT}/vidgenerator/debugger/index.html 2>&1",
            timeout=10
        )
        mtime = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"  debugger/index.html: {mtime}")
        
    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    verify()
