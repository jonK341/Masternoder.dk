"""
Deploy enhanced_stats_tracking.py service to correct location
"""
import paramiko
import os
from scp import SCPClient
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def deploy():
    """Deploy service to correct location"""
    try:
        print("=" * 70)
        print("DEPLOYING ENHANCED_STATS_TRACKING SERVICE")
        print("=" * 70)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected to server")
        
        # Ensure directory exists
        print("\n[1] Ensuring directory exists...")
        stdin, stdout, stderr = ssh.exec_command('mkdir -p /var/www/html/vidgenerator/backend/services')
        result = stdout.read().decode('utf-8', errors='replace')
        
        # Deploy service file
        local_file = "backend/services/enhanced_stats_tracking.py"
        remote_file = "/var/www/html/vidgenerator/backend/services/enhanced_stats_tracking.py"
        
        print(f"\n[2] Uploading {local_file} to {remote_file}...")
        scp = SCPClient(ssh.get_transport())
        scp.put(local_file, remote_file)
        scp.close()
        print(f"[OK] File uploaded")
        
        # Clear Python cache
        print("\n[3] Clearing Python cache...")
        stdin, stdout, stderr = ssh.exec_command('find /var/www/html/vidgenerator/backend -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null; find /var/www/html/vidgenerator/backend -name "*.pyc" -delete 2>/dev/null; echo "Cache cleared"')
        cache_result = stdout.read().decode('utf-8', errors='replace')
        print(cache_result)
        
        # Restart uwsgi
        print("\n[4] Restarting uwsgi-vidgenerator service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl restart uwsgi-vidgenerator.service 2>&1')
        restart_result = stdout.read().decode('utf-8', errors='replace')
        if restart_result:
            print(restart_result)
        print("[OK] Service restarted")
        
        print("\n[5] Waiting 5 seconds for service to start...")
        time.sleep(5)
        
        print("\n" + "=" * 70)
        print("[OK] Deployment complete!")
        print("=" * 70)
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy()

