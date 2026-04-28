#!/usr/bin/env python3
"""
Remove duplicate profile routes from blueprints - only keep direct route in app.py
"""
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
    print("REMOVING DUPLICATE PROFILE ROUTES")
    print("=" * 80)
    print("Keeping only the direct route in app.py")
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    print("\nDeploying files...")
    scp.put("backend/routes/stats.py", f"{REMOTE_PATH}/backend/routes/stats.py")
    print("[OK] Removed profile route from stats.py")
    
    scp.put("backend/routes/game.py", f"{REMOTE_PATH}/backend/routes/game.py")
    print("[OK] Removed profile route from game.py")
    
    scp.put("backend/routes/profile.py", f"{REMOTE_PATH}/backend/routes/profile.py")
    print("[OK] Disabled profile route in profile.py")
    
    scp.close()
    
    print("\nClearing cache and restarting...")
    stdin, stdout, stderr = ssh_client.exec_command("find /var/www/html/vidgenerator -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; find /var/www/html/vidgenerator -name '*.pyc' -delete 2>/dev/null; systemctl restart uwsgi && sleep 5 && systemctl restart python-proxy.service")
    stdout.channel.recv_exit_status()
    print("[OK] Services restarted")
    
    print("\nWaiting 15 seconds...")
    import time
    time.sleep(15)
    
    print("\nTesting profile route...")
    stdin, stdout, stderr = ssh_client.exec_command("curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/profile 2>&1")
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    print(f"Profile route status: {output}")
    
    if output == "200":
        print("\n" + "=" * 80)
        print("SUCCESS! Profile route is working!")
        print("=" * 80)
    else:
        print(f"\nStill {output}")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    ssh_client.close()

