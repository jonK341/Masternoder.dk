"""
Deploy updated game page with enhanced stats integration
"""
import paramiko
import os
from scp import SCPClient
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def deploy():
    """Deploy updated game page"""
    try:
        print("=" * 70)
        print("DEPLOYING UPDATED GAME PAGE WITH ENHANCED STATS")
        print("=" * 70)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected to server")
        
        # Deploy game page
        local_file = "vidgenerator/game/index.html"
        remote_file = f"{REMOTE_PATH}/game/index.html"
        
        print(f"\n[1] Uploading {local_file}...")
        scp = SCPClient(ssh.get_transport())
        scp.put(local_file, remote_file)
        scp.close()
        print(f"[OK] File uploaded to {remote_file}")
        
        print("\n" + "=" * 70)
        print("[OK] Deployment complete!")
        print("=" * 70)
        print("\nNote: No service restart needed - static HTML file deployed")
        
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    deploy()

