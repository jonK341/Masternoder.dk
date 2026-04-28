#!/usr/bin/env python3
"""
Quick uWSGI restart
"""

import paramiko
import time

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def restart():
    """Restart uWSGI"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("Restarting uWSGI...")
        cmd = "sudo systemctl restart uwsgi-vidgenerator.service && sleep 3"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        print("✅ Restarted!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        ssh_client.close()

if __name__ == '__main__':
    restart()

import os
