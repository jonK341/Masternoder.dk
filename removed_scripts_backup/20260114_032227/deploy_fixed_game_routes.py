"""
Deploy fixed game.py routes file
"""
import paramiko
import os
from scp import SCPClient

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html"

def deploy():
    """Deploy fixed game.py"""
    try:
        print("=" * 70)
        print("DEPLOYING FIXED game.py")
        print("=" * 70)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected to server")
        
        # Deploy file
        local_file = "backend/routes/game.py"
        remote_file = f"{REMOTE_PATH}/backend/routes/game.py"
        
        print(f"\n[1] Uploading {local_file}...")
        scp = SCPClient(ssh.get_transport())
        scp.put(local_file, remote_file)
        scp.close()
        print(f"[OK] File uploaded to {remote_file}")
        
        # Clear Python cache
        print("\n[2] Clearing Python cache...")
        stdin, stdout, stderr = ssh.exec_command(f'find {REMOTE_PATH}/backend -type d -name "__pycache__" -exec rm -r {{}} + 2>/dev/null; find {REMOTE_PATH}/backend -name "*.pyc" -delete 2>/dev/null; echo "Cache cleared"')
        cache_result = stdout.read().decode('utf-8', errors='replace')
        print(cache_result)
        
        # Restart uwsgi
        print("\n[3] Restarting uwsgi-vidgenerator service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl restart uwsgi-vidgenerator.service 2>&1')
        restart_result = stdout.read().decode('utf-8', errors='replace')
        if restart_result:
            print(restart_result)
        print("[OK] Service restarted")
        
        print("\n[4] Waiting 5 seconds for service to start...")
        import time
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

