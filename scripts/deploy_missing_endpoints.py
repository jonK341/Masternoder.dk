#!/usr/bin/env python3
"""
Deploy Missing Endpoints - Deploy routes for missing endpoints
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"

FILES_TO_DEPLOY = [
    "backend/routes/missing_endpoints_routes.py",
    "backend/register_blueprints.py"
]

def deploy_missing_endpoints():
    """Deploy missing endpoints routes"""
    print("=" * 70)
    print("Deploy Missing Endpoints - Production")
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
        print("[2/5] Deploying files...")
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                remote_file = f"{REMOTE_BASE}/{local_file.replace(chr(92), '/')}"
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
        
        sftp.close()
        print(f"  [SUMMARY] {deployed} files deployed")
        print()
        
        # Clear cache
        print("[3/5] Clearing cache...")
        ssh.exec_command(f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
        ssh.exec_command(f"find {REMOTE_BASE} -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
        time.sleep(15)
        ssh.exec_command("systemctl restart python-proxy", timeout=5)
        time.sleep(5)
        print("  [OK] Services restarted")
        print()
        
        # Verify
        print("[5/5] Verifying...")
        time.sleep(5)
        
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
        print("✅ Missing Endpoints Deployed!")
        print("=" * 70)
        print()
        print("Added 18 missing endpoint routes:")
        print("  - Points (comprehensive, statistics, history/analytics, calculator/predict)")
        print("  - Monetization (top50, cash)")
        print("  - Tech Tree (knowledge, main)")
        print("  - Game Mechanics (progress, achievements)")
        print("  - Ultra Resource (energy)")
        print("  - Agent (get-all, recommendations)")
        print("  - Aggregator (stats, unified-dashboard)")
        print("  - Intelligence Aggregator (status)")
        print("  - Trophies (user)")
        print("  - Debugger (status)")
        print()
        print("Next Steps:")
        print("  1. Wait 15-20 seconds for services to fully initialize")
        print("  2. Test endpoints: python scripts/test_all_endpoints.py")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_missing_endpoints()
    sys.exit(0 if success else 1)
