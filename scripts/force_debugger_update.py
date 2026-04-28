#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Force Debugger Update
Directly updates the file and clears all caches
"""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def force_update():
    """Force update debugger file"""
    ssh = None
    sftp = None
    try:
        print("Connecting...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Read local file
        with open('vidgenerator/debugger/index.html', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Write to server
        remote_path = '/var/www/html/vidgenerator/debugger/index.html'
        with sftp.open(remote_path, 'w') as f:
            f.write(content)
        
        print("File written")
        
        # Clear all caches
        print("Clearing caches...")
        ssh.exec_command("rm -rf /var/cache/nginx/* 2>&1", timeout=10)
        ssh.exec_command("find /var/www/html -name '*.pyc' -delete 2>&1", timeout=10)
        ssh.exec_command("find /var/www/html -name '__pycache__' -type d -exec rm -rf {} + 2>&1", timeout=10)
        
        # Restart everything
        print("Restarting services...")
        ssh.exec_command("systemctl restart python-proxy.service 2>&1", timeout=30)
        ssh.exec_command("systemctl restart uwsgi-vidgenerator 2>&1 || true", timeout=30)
        ssh.exec_command("systemctl restart nginx 2>&1", timeout=30)
        ssh.exec_command("systemctl restart apache2 2>&1 || true", timeout=30)
        
        print("Done!")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == '__main__':
    force_update()
