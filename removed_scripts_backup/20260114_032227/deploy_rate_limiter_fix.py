#!/usr/bin/env python3
"""
Deploy Rate Limiter Fix
"""
import paramiko
from scp import SCPClient
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = '/var/www/html/vidgenerator'

def deploy_fix():
    """Deploy rate limiter fix"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        scp = SCPClient(ssh.get_transport())
        
        # Deploy rate_limiter.py fix
        scp.put('src/utils/rate_limiter.py', f'{REMOTE_BASE}/src/utils/rate_limiter.py')
        print("[OK] Deployed rate_limiter.py fix")
        
        # Restart uWSGI
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] uWSGI restarted")
        else:
            print(f"[WARN] uWSGI restart exit code: {exit_status}")
        
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    deploy_fix()

