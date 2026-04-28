#!/usr/bin/env python3
"""
Get Full Nginx Location
Gets the full location block for /vidgenerator
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def get_config():
    """Get full nginx location block"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Get lines around the location /vidgenerator/ block
        cmd = f"grep -n 'location /vidgenerator/' {nginx_config}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        line_num = stdout.read().decode().strip().split(':')[0]
        
        if line_num:
            # Get 15 lines starting from that line
            cmd2 = f"sed -n '{line_num},+15p' {nginx_config}"
            stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
            output = stdout2.read().decode().strip()
            print("Location /vidgenerator/ block:")
            print(output)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    get_config()
