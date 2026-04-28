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
    print("=" * 80)
    print("DEPLOYING PROFILE DIRECT ROUTE")
    print("=" * 80)
    print("Connecting to server...")
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    
    scp = SCPClient(ssh_client.get_transport())
    
    print("\nDeploying files...")
    print("-" * 80)
    scp.put("src/app.py", f"{REMOTE_PATH}/src/app.py")
    print("[OK] Deployed src/app.py with direct profile route")
    
    scp.close()
    
    print("\nClearing Python cache...")
    print("-" * 80)
    stdin, stdout, stderr = ssh_client.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true")
    stdout.channel.recv_exit_status()
    print("[OK] Cache cleared")
    
    print("\nRestarting services...")
    print("-" * 80)
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code == 0:
        print("[OK] systemctl restart uwsgi")
    else:
        print(f"[WARN] systemctl restart uwsgi - Exit code: {exit_code}")
    
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart python-proxy.service")
    exit_code = stdout.channel.recv_exit_status()
    if exit_code == 0:
        print("[OK] systemctl restart python-proxy.service")
    else:
        print(f"[WARN] systemctl restart python-proxy.service - Exit code: {exit_code}")
    
    print("\n" + "=" * 80)
    print("[OK] DEPLOYMENT COMPLETE")
    print("=" * 80)
    print("\nProfile route added as DIRECT route in app.py")
    print("URL: https://masternoder.dk/vidgenerator/profile")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    ssh_client.close()

