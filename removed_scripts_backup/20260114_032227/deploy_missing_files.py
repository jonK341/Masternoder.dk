"""Deploy missing redesigned files"""
import paramiko
from scp import SCPClient
import os

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def deploy_missing():
    """Deploy missing files"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Deploying Missing Files")
        print("=" * 70)
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        print("[OK] Connected!")
        print()
        
        # Files to deploy
        files = [
            ('vidgenerator/index.html', '/var/www/html/vidgenerator/index.html'),
            ('vidgenerator/static/css/modern-design-system.css', '/var/www/html/vidgenerator/static/css/modern-design-system.css'),
        ]
        
        with SCPClient(ssh.get_transport()) as scp:
            for local, remote in files:
                if os.path.exists(local):
                    print(f"Deploying {local}...")
                    # Create directory if needed
                    remote_dir = os.path.dirname(remote)
                    ssh.exec_command(f'mkdir -p {remote_dir}')
                    
                    scp.put(local, remote)
                    print(f"[OK] Deployed to {remote}")
                else:
                    print(f"[WARN] {local} not found")
        
        print()
        print("=" * 70)
        print("[OK] Missing files deployed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()

if __name__ == '__main__':
    deploy_missing()

