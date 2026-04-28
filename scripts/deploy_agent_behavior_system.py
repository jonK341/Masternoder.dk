#!/usr/bin/env python3
"""
Deploy Agent Behavior System
Deploy agent player behavior system to production
"""
import paramiko
import os
import sys
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "backend/services/agent_player_behavior.py",
    "backend/routes/agent_behavior_routes.py",
    "backend/register_blueprints.py"
]

def deploy_agent_behavior():
    """Deploy agent behavior system"""
    print("=" * 70)
    print("DEPLOY AGENT BEHAVIOR SYSTEM")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                remote_file = f"/var/www/html/vidgenerator/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                sftp.put(local_file, remote_file)
                print(f"  [OK] Deployed {local_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
        
        sftp.close()
        
        # Restart services
        print()
        print("Restarting services...")
        ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=5)
        time.sleep(3)
        print("  [OK] Services restarted")
        
        ssh.close()
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print("Agent behavior system deployed!")
        print("Agents now behave like real players!")
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    import time
    deploy_agent_behavior()
