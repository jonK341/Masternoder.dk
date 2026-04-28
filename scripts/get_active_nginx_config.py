#!/usr/bin/env python3
"""
Get Active Nginx Config
Gets the active nginx configuration (not commented out)
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def get_config():
    """Get active nginx config"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Get the active HTTPS server block (port 443, not commented)
        print("Getting active HTTPS server block...")
        print()
        
        # Find the line with "listen 443" that's not commented
        cmd = f"grep -n 'listen 443' {nginx_config} | grep -v '^[[:space:]]*#' | head -1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        line_info = stdout.read().decode().strip()
        
        if line_info:
            line_num = int(line_info.split(':')[0])
            # Get 80 lines from that point
            cmd2 = f"sed -n '{line_num},+80p' {nginx_config}"
            stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
            output = stdout2.read().decode().strip()
            print(output)
        else:
            print("  [ERROR] Could not find active HTTPS server block")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    get_config()
