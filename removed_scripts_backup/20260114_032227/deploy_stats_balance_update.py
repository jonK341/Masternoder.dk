"""
Deploy stats balance update to server
"""
import paramiko
import os
import sys
import time
from scp import SCPClient

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv('DEPLOY_HOST', 'masternoder.dk')
USERNAME = os.getenv('DEPLOY_USER', 'root')
PASSWORD = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_PATH = os.getenv('DEPLOY_PATH', '/var/www/html/vidgenerator')

print("=" * 80)
print("DEPLOYING STATS BALANCE UPDATE")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # File to deploy
    local_file = "backend/routes/stats.py"
    remote_file = f"{REMOTE_PATH}/backend/routes/stats.py"
    
    if not os.path.exists(local_file):
        print(f"[ERROR] Local file not found: {local_file}")
        exit(1)
    
    print(f"[1] Uploading {local_file}...")
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_file, remote_file)
    print("[OK] File uploaded")
    
    # Restart Flask service
    print("[2] Restarting Flask service...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service")
    time.sleep(2)
    
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active python-proxy.service")
    status = stdout.read().decode('utf-8').strip()
    if status == "active":
        print("[OK] Flask service restarted")
    else:
        print(f"[WARN] Flask service status: {status}")
    
    print()
    print("=" * 80)
    print("[OK] Stats balance update deployed!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

