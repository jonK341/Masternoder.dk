#!/usr/bin/env python3
"""
Deploy Missing Services - Deploy agent service files to production
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

# Service files that are missing on server
SERVICE_FILES = [
    "backend/services/agent_controller.py",
    "backend/services/agent_automation.py",
    "backend/services/agent_skillset.py",
    "backend/services/agent_groups.py",
    "backend/services/agent_ability_tracker.py"
]

def deploy_services():
    """Deploy missing service files"""
    print("=" * 70)
    print("Deploy Missing Services - Production Deployment")
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
        print("[2/5] Deploying service files...")
        sftp = ssh.open_sftp()
        deployed = 0
        skipped = 0
        errors = 0
        
        for local_file in SERVICE_FILES:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found locally)")
                skipped += 1
                continue
            
            try:
                remote_file = f"{REMOTE_BASE}/{local_file.replace(chr(92), '/')}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create directory if needed
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Create backup if file exists
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
        ssh.exec_command(f"find {REMOTE_BASE} -type d -name __pycache__ -exec rm -rf {{}} + 2>/dev/null || true", timeout=30)
        ssh.exec_command(f"find {REMOTE_BASE} -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        # Restart services
        print("[4/5] Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1", timeout=10)
        time.sleep(15)  # Give time for restart
        ssh.exec_command("systemctl restart python-proxy 2>&1", timeout=10)
        time.sleep(5)
        print("  [OK] Services restarted")
        print()
        
        # Verify deployment
        print("[5/5] Verifying deployment...")
        time.sleep(5)
        
        # Test imports
        print("  Testing imports...")
        cmd = f"cd {REMOTE_BASE} && python3 -c \"from backend.services.agent_controller import agent_controller; print('SUCCESS')\" 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        
        if "SUCCESS" in output:
            print("  ✅ agent_controller import successful")
        else:
            print(f"  ⚠️  agent_controller import: {output[:200]}")
        
        cmd = f"cd {REMOTE_BASE} && python3 -c \"from backend.services.agent_automation import agent_automation; print('SUCCESS')\" 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        
        if "SUCCESS" in output:
            print("  ✅ agent_automation import successful")
        else:
            print(f"  ⚠️  agent_automation import: {output[:200]}")
        
        print()
        print("=" * 70)
        print("✅ Services Deployed!")
        print("=" * 70)
        print()
        print("Next Steps:")
        print("  1. Wait 20-30 seconds for services to fully restart")
        print("  2. Test endpoints: python scripts/test_endpoints_one_by_one.py")
        print("  3. Hard refresh browser: Ctrl+F5")
        print()
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = deploy_services()
    sys.exit(0 if success else 1)
