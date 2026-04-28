#!/usr/bin/env python3
"""
Deploy Points Route Fix
Deploys the points page route fix
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "backend/routes/dashboard_page_routes.py",
    "backend/register_blueprints.py"
]

def deploy_points_route():
    """Deploy points route fix"""
    print("=" * 70)
    print("Points Route Fix - Production Deployment")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/4] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/4] Deploying files...")
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                remote_file = f"/var/www/html/vidgenerator/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create remote directory
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Backup existing file
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                # Copy file
                sftp.put(local_file, remote_file)
                print(f"  [OK] Deployed {local_file}")
                deployed += 1
                
            except Exception as e:
                print(f"  [ERROR] Failed to deploy {local_file}: {e}")
        
        sftp.close()
        print(f"  [SUMMARY] Deployed {deployed}/{len(FILES_TO_DEPLOY)} files")
        print()
        
        # Clear cache
        print("[3/4] Clearing Python cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/4] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
        time.sleep(2)
        ssh.exec_command("systemctl restart python-proxy", timeout=5)
        time.sleep(2)
        print("  [OK] Services restarted")
        print()
        
        # Verify services
        print("[VERIFY] Checking service status...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        uwsgi_status = stdout.read().decode().strip()
        if uwsgi_status == 'active':
            print("  [OK] uWSGI is active")
        else:
            print(f"  [WARN] uWSGI status: {uwsgi_status}")
        
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy", timeout=5)
        proxy_status = stdout.read().decode().strip()
        if proxy_status == 'active':
            print("  [OK] python-proxy is active")
        else:
            print(f"  [WARN] python-proxy status: {proxy_status}")
        
        ssh.close()
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Test: https://masternoder.dk/vidgenerator/points")
        print("  2. Hard refresh browser (Ctrl+F5)")
        print()
        
    except Exception as e:
        print(f"\n  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    deploy_points_route()
