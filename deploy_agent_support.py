#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy Agent Support to Production
Deploys agent support routes and HTML page
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

# Files to deploy
FILES_TO_DEPLOY = [
    "backend/routes/agent_support_routes.py",
    "vidgenerator/agent_support/index.html"
]

def deploy():
    """Deploy agent support files to production"""
    print("="*80)
    print("DEPLOYING AGENT SUPPORT TO PRODUCTION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect
        print("[1/5] Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/5] Deploying files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                skipped += 1
                continue
                
            try:
                remote_file = f"/var/www/html/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                with open(local_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                with sftp.file(remote_file, 'w') as rf:
                    rf.write(content)
                
                print(f"  [OK] {local_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
        
        sftp.close()
        print(f"  [SUMMARY] {deployed} deployed, {skipped} skipped")
        print()
        
        # Clear cache
        print("[3/5] Clearing cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        for service in ['uwsgi-vidgenerator']:
            ssh.exec_command(f"systemctl restart {service} 2>&1", timeout=10)
        time.sleep(8)
        
        # Verify
        print("[5/5] Verifying services...")
        for service in ['uwsgi-vidgenerator']:
            stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {service} 2>&1", timeout=5)
            status = stdout.read().decode().strip()
            if status == "active":
                print(f"  [OK] {service} is ACTIVE")
            else:
                print(f"  [WARN] {service} status: {status}")
        
        print()
        print("="*70)
        print("DEPLOYMENT COMPLETE!")
        print("="*70)
        print()
        print("Agent Support deployed successfully!")
        print("Visit: https://masternoder.dk/vidgenerator/agent_support/")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy()
    sys.exit(0 if success else 1)
