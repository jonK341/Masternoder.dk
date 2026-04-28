#!/usr/bin/env python3
"""
Deploy blueprint registration update
"""
import paramiko
from scp import SCPClient
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = 'masternoder.dk'
SERVER_USER = 'root'
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

def deploy():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print(f"Connected to {SERVER_HOST}")
        
        scp = SCPClient(ssh.get_transport())
        remote_path = f"{REMOTE_BASE}/backend/register_blueprints.py"
        scp.put('backend/register_blueprints.py', remote_path)
        print(f"Deployed: backend/register_blueprints.py -> {remote_path}")
        ssh.exec_command(f"chmod 644 {remote_path}")
        ssh.exec_command("systemctl restart uwsgi")
        print("uWSGI restarted")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = deploy()
    exit(0 if success else 1)

