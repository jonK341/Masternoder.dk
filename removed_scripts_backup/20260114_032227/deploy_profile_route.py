#!/usr/bin/env python3
import os
import sys
import paramiko
from scp import SCPClient

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print("Connecting to server...")
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    
    scp = SCPClient(ssh_client.get_transport())
    scp.put("backend/routes/game.py", f"{REMOTE_PATH}/backend/routes/game.py")
    print("[OK] Deployed game.py with profile route")
    scp.close()
    
    print("Restarting services...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
    stdout.channel.recv_exit_status()
    print("[OK] Services restarted")
    
except Exception as e:
    print(f"[ERROR] {e}")
finally:
    ssh_client.close()

