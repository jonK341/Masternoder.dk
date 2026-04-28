#!/usr/bin/env python3
"""
Deploy URL Fixes - Fix 404 errors in agent dashboard data
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

# Fixed files
FIXED_FILES = [
    "vidgenerator/static/js/agent-dashboard-data.js"
]

# Updated HTML files with new cache version
UPDATED_HTML_FILES = [
    "vidgenerator/unified_dashboard/index.html",
    "vidgenerator/dashboard/index.html",
    "vidgenerator/aggregator/index.html",
    "vidgenerator/analytics/index.html",
    "vidgenerator/admin/analytics.html",
    "vidgenerator/leaderboards/index.html",
    "vidgenerator/index.html"
]

ALL_FILES = FIXED_FILES + UPDATED_HTML_FILES

def deploy_fixes():
    """Deploy URL fixes"""
    print("=" * 70)
    print("URL Fixes - Production Deployment")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/5] Deploying fixed files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in ALL_FILES:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                skipped += 1
                continue
            
            try:
                remote_file = f"/var/www/html/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create directory if needed
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Create backup
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                # Read and write file
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(content)
                
                print(f"  [OK] {local_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
                errors += 1
        
        sftp.close()
        print(f"  [SUMMARY] {deployed} deployed, {skipped} skipped, {errors} errors")
        print()
        
        # Clear cache
        print("[3/5] Clearing server cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(5)
        ssh.exec_command("systemctl restart python-proxy 2>&1", timeout=10)
        time.sleep(5)
        print("  [OK] Services restarted")
        print()
        
        # Verify deployment
        print("[5/5] Verifying deployment...")
        time.sleep(3)
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        uwsgi_status = stdout.read().decode().strip()
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy", timeout=5)
        proxy_status = stdout.read().decode().strip()
        
        if uwsgi_status == "active":
            print("  [OK] uwsgi-vidgenerator is active")
        else:
            print(f"  [WARN] uwsgi-vidgenerator status: {uwsgi_status}")
        
        if proxy_status == "active":
            print("  [OK] python-proxy is active")
        else:
            print(f"  [WARN] python-proxy status: {proxy_status}")
        
        print()
        print("=" * 70)
        print("✅ URL Fixes Deployed!")
        print("=" * 70)
        print()
        print("Fixed URLs:")
        print("  - /agents/controller/status → /agent-controller/status")
        print("  - /agents/skillsets/stats → /agent/skillset/stats")
        print()
        print("Next Steps:")
        print("  1. Hard refresh browser: Ctrl+F5")
        print("  2. Check browser console (F12) for errors")
        print("  3. Verify agent data loads in dashboards")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_fixes()
    sys.exit(0 if success else 1)
