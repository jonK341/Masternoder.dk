#!/usr/bin/env python3
"""
Check Nginx Rewrite
Checks nginx configuration for URL rewriting rules
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_nginx():
    """Check nginx rewrite rules"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        print("Checking nginx rewrite rules for /vidgenerator/api/...")
        print()
        
        # Check for rewrite rules
        cmd = f"grep -A 5 -B 5 'location.*vidgenerator' {nginx_config} | head -30"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        print(output)
        
        print()
        print("Checking for rewrite rules...")
        cmd2 = f"grep -n 'rewrite.*vidgenerator' {nginx_config}"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
        output2 = stdout2.read().decode().strip()
        if output2:
            print(output2)
        else:
            print("  [WARN] No rewrite rules found for vidgenerator")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    check_nginx()
