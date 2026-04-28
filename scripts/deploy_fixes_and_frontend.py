#!/usr/bin/env python3
"""
Deploy Fixes and Frontend
Deploys all fixes, debugger enhancements, and frontend files
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
    "backend/services/production_debugger.py",
    "backend/routes/production_debugger_routes.py",
    "backend/routes/system_aggregator_routes.py",
    "backend/register_blueprints.py",
    "vidgenerator/debugger/index.html",
]

def deploy_files():
    """Deploy files to production"""
    print("="*80)
    print("DEPLOYING FIXES AND FRONTEND")
    print("="*80)
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
        errors = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                skipped += 1
                continue
                
            try:
                remote_file = f"/var/www/html/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
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
        print("[3/5] Clearing cache...")
        ssh.exec_command("find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(15)
        print("  [OK] Services restarted")
        print()
        
        # Verify
        print("[5/5] Verifying services...")
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator 2>&1", timeout=5)
        status = stdout.read().decode().strip()
        if status == "active":
            print(f"  [OK] uwsgi-vidgenerator is ACTIVE")
        else:
            print(f"  [WARN] uwsgi-vidgenerator status: {status}")
        
        print()
        print("="*80)
        print("DEPLOYMENT COMPLETE")
        print("="*80)
        print(f"Deployed: {deployed} files")
        print(f"Skipped: {skipped} files")
        print(f"Errors: {errors} files")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_files()
    sys.exit(0 if success else 1)
