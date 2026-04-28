#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verify and Fix Debugger Page
Checks if Error Dashboard tab exists on server and redeploys if needed
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify_and_fix():
    """Verify debugger page and fix if needed"""
    print("=" * 70)
    print("VERIFYING AND FIXING DEBUGGER PAGE")
    print("=" * 70)
    print()
    
    ssh = None
    sftp = None
    try:
        print("[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        print("  [OK] Connected")
        print()
        
        # Check if Error Dashboard exists
        print("[2/4] Checking for Error Dashboard tab...")
        stdin, stdout, stderr = ssh.exec_command(
            "grep -c 'Error Dashboard' /var/www/html/vidgenerator/debugger/index.html 2>&1",
            timeout=10
        )
        count = stdout.read().decode('utf-8', errors='ignore').strip()
        if count and count.isdigit() and int(count) > 0:
            print(f"  [OK] Found {count} references to Error Dashboard")
        else:
            print("  [ERROR] Error Dashboard tab NOT FOUND on server!")
            print("  [INFO] Will redeploy file...")
        print()
        
        # Read local file
        print("[3/4] Reading local debugger file...")
        local_path = 'vidgenerator/debugger/index.html'
        if not os.path.exists(local_path):
            print(f"  [ERROR] Local file not found: {local_path}")
            return False
        
        with open(local_path, 'r', encoding='utf-8') as f:
            local_content = f.read()
        
        if 'Error Dashboard' not in local_content:
            print("  [ERROR] Error Dashboard not in local file!")
            return False
        
        print(f"  [OK] Local file has Error Dashboard ({len(local_content)} bytes)")
        print()
        
        # Deploy to server
        print("[4/4] Deploying to server...")
        remote_path = '/var/www/html/vidgenerator/debugger/index.html'
        
        # Backup existing file
        try:
            stdin, stdout, stderr = ssh.exec_command(
                f"cp {remote_path} {remote_path}.backup.$(date +%Y%m%d_%H%M%S) 2>&1",
                timeout=10
            )
            print("  [OK] Backup created")
        except:
            pass
        
        # Write new file
        with sftp.open(remote_path, 'w') as f:
            f.write(local_content)
        
        print(f"  [OK] File deployed to {remote_path}")
        print()
        
        # Verify deployment
        stdin, stdout, stderr = ssh.exec_command(
            "grep -c 'Error Dashboard' /var/www/html/vidgenerator/debugger/index.html 2>&1",
            timeout=10
        )
        count = stdout.read().decode('utf-8', errors='ignore').strip()
        if count and count.isdigit() and int(count) > 0:
            print(f"  [OK] Verified: {count} references found on server")
        else:
            print("  [WARN] Verification failed - tab may still be missing")
        print()
        
        # Restart services
        print("Restarting services...")
        ssh.exec_command("systemctl restart python-proxy.service 2>&1", timeout=30)
        ssh.exec_command("systemctl restart nginx 2>&1", timeout=30)
        print("  [OK] Services restarted")
        print()
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Hard refresh browser: Ctrl+Shift+R")
        print("  2. Visit: https://masternoder.dk/vidgenerator/debugger")
        print("  3. Look for '🚨 Error Dashboard' tab")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == '__main__':
    success = verify_and_fix()
    sys.exit(0 if success else 1)
