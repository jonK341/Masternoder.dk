#!/usr/bin/env python3
"""
Get Full Nginx Config
Gets the full nginx configuration for analysis
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def get_config():
    """Get full nginx config"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Get the server block for HTTPS (port 443)
        print("Getting HTTPS server block (port 443)...")
        print()
        cmd = f"sed -n '/listen 443/,/^[[:space:]]*server[[:space:]]*{{/p' {nginx_config} | head -100"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        print(output)
        
        # Also check for location /vidgenerator/ specifically
        print()
        print("="*70)
        print("Location blocks for /vidgenerator:")
        print("="*70)
        cmd2 = f"grep -n 'location.*vidgenerator' {nginx_config}"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
        output2 = stdout2.read().decode().strip()
        print(output2)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    get_config()
