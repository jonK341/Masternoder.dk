#!/usr/bin/env python3
"""
Check Nginx Proxy Pass
Checks nginx proxy_pass configuration
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_nginx():
    """Check nginx proxy_pass"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        print("Checking nginx proxy_pass configuration...")
        print()
        
        # Check for location blocks that handle /vidgenerator
        cmd = f"grep -A 10 'location.*vidgenerator' {nginx_config} | grep -A 10 'proxy_pass'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        if output:
            print(output)
        else:
            print("  [WARN] No proxy_pass found in vidgenerator location block")
        
        # Check the full location block
        print()
        print("Full location block for /vidgenerator:")
        cmd2 = f"sed -n '/location.*vidgenerator/,/^[[:space:]]*[^[:space:]]/p' {nginx_config} | head -20"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
        output2 = stdout2.read().decode().strip()
        print(output2)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    check_nginx()
