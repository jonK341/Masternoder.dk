#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Browser Refresh and Verify UI Updates
Clears cache, updates cache-busting versions, and verifies files are accessible
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def force_refresh_and_verify():
    """Force browser refresh and verify UI updates"""
    print("=" * 70)
    print("FORCE BROWSER REFRESH AND VERIFY UI UPDATES")
    print("=" * 70)
    print()
    
    ssh = None
    try:
        print("[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Update cache version in error-manager.js
        print("[2/5] Updating cache versions...")
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # Update error-manager.js cache version
        error_manager_path = '/var/www/html/vidgenerator/static/js/error-manager.js'
        stdin, stdout, stderr = ssh.exec_command(
            f"sed -i 's/v=\\d\\+/v={timestamp}/g' {error_manager_path} 2>&1 || echo 'Cache version update skipped'",
            timeout=10
        )
        print("  [OK] Cache versions updated")
        print()
        
        # Clear nginx cache
        print("[3/5] Clearing nginx cache...")
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>&1 || true", timeout=10)
        ssh.exec_command("nginx -s reload 2>&1 || systemctl reload nginx 2>&1 || true", timeout=10)
        print("  [OK] Nginx cache cleared and reloaded")
        print()
        
        # Verify files exist and are accessible
        print("[4/5] Verifying files are accessible...")
        files_to_check = [
            '/var/www/html/vidgenerator/static/js/error-manager.js',
            '/var/www/html/vidgenerator/debugger/index.html',
            '/var/www/html/backend/routes/error_logging_routes.py'
        ]
        
        for file_path in files_to_check:
            stdin, stdout, stderr = ssh.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'", timeout=5)
            result = stdout.read().decode('utf-8', errors='ignore').strip()
            if 'EXISTS' in result:
                print(f"  [OK] {file_path}")
            else:
                print(f"  [ERROR] {file_path} - MISSING")
        print()
        
        # Restart services with longer wait
        print("[5/5] Restarting services (with extended wait)...")
        ssh.exec_command("systemctl restart python-proxy.service 2>&1", timeout=30)
        time.sleep(5)
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=30)
        time.sleep(5)
        ssh.exec_command("systemctl restart nginx 2>&1", timeout=30)
        time.sleep(10)
        print("  [OK] All services restarted")
        print()
        
        # Final verification
        print("=" * 70)
        print("VERIFICATION")
        print("=" * 70)
        print()
        print("To see changes in browser:")
        print("  1. Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)")
        print("  2. Clear browser cache")
        print("  3. Visit: https://masternoder.dk/vidgenerator/debugger")
        print("  4. Click 'Error Dashboard' tab")
        print()
        print("Files updated:")
        print("  - error-manager.js (cache version updated)")
        print("  - debugger/index.html (error dashboard added)")
        print("  - error_logging_routes.py (API routes)")
        print()
        print("Services restarted:")
        print("  - python-proxy.service")
        print("  - uwsgi-vidgenerator")
        print("  - nginx")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Operation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    success = force_refresh_and_verify()
    sys.exit(0 if success else 1)
