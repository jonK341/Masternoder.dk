#!/usr/bin/env python3
"""
Deploy 50 Agent Technologies to Production
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TECH_DIR = os.path.join(BASE_DIR, 'backend', 'services', 'agent_techs')
ROUTES_DIR = os.path.join(BASE_DIR, 'backend', 'routes')

def get_tech_files():
    """Get all tech files to deploy"""
    files = []
    
    # Tech services
    if os.path.exists(TECH_DIR):
        for filename in os.listdir(TECH_DIR):
            if filename.endswith('.py'):
                files.append(f"backend/services/agent_techs/{filename}")
    
    # Tech routes - ALL 50 tech routes
    for filename in os.listdir(ROUTES_DIR):
        if filename.endswith('_routes.py') and 'agent_' in filename:
            files.append(f"backend/routes/{filename}")
    
    # Core files
    files.extend([
        "backend/services/agent_techs/__init__.py",
        "backend/register_blueprints.py",
        "vidgenerator/static/js/agent-techs-manager.js",
        "vidgenerator/unified_dashboard/index.html"
    ])
    
    return files

def deploy_50_techs():
    """Deploy all 50 techs"""
    print("=" * 70)
    print("DEPLOYING 50 AGENT TECHNOLOGIES")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect
        print("[1/5] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Get files
        files_to_deploy = get_tech_files()
        print(f"[2/5] Deploying {len(files_to_deploy)} files...")
        
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in files_to_deploy:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                remote_file = f"/var/www/html/vidgenerator/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create directory
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Backup
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                # Deploy
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
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        ssh.exec_command("systemctl restart python-proxy 2>&1", timeout=10)
        print("  [OK] Restart commands sent")
        print()
        
        # Verify
        print("[5/5] Verifying...")
        time.sleep(5)
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator", timeout=5)
        status = stdout.read().decode().strip()
        print(f"  [STATUS] uwsgi-vidgenerator: {status}")
        print()
        
        ssh.close()
        
        print("=" * 70)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 70)
        print(f"\nDeployed {deployed} files")
        print("\nNext: Run test script to verify all techs work")
        print("  python scripts/test_50_agent_techs.py")
        
    except Exception as e:
        print(f"\n❌ DEPLOYMENT FAILED: {e}")
        sys.exit(1)

if __name__ == '__main__':
    deploy_50_techs()
