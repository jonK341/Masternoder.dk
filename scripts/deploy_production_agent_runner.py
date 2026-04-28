#!/usr/bin/env python3
"""Deploy production agent runner to server"""
import paramiko
import os
import sys
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "scripts/production_agent_runner.py",
    "scripts/start_production_agents.sh"
]

def deploy():
    """Deploy production agent runner"""
    print("=" * 70)
    print("DEPLOY PRODUCTION AGENT RUNNER")
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
                
                # Make shell script executable
                if local_file.endswith('.sh'):
                    ssh.exec_command(f"chmod +x {remote_file} 2>&1", timeout=5)
                
                print(f"  [OK] Deployed {local_file}")
                deployed += 1
            except Exception as e:
                print(f"  [ERROR] {local_file}: {e}")
        
        sftp.close()
        
        # Create logs directory
        ssh.exec_command("mkdir -p /var/www/html/vidgenerator/logs/agents 2>&1", timeout=5)
        
        print()
        print(f"  [SUMMARY] Deployed {deployed}/{len(FILES_TO_DEPLOY)} files")
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("To start agents in production:")
        print("  ssh root@masternoder.dk")
        print("  cd /var/www/html/vidgenerator")
        print("  python3 scripts/production_agent_runner.py")
        print("  # Or use: bash scripts/start_production_agents.sh")
        print()
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    deploy()
