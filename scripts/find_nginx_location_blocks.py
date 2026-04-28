#!/usr/bin/env python3
"""
Find Nginx Location Blocks
Finds all location blocks in nginx config
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def find_blocks():
    """Find location blocks"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Get the entire file and find server blocks
        print("Finding server blocks and their location blocks...")
        print()
        
        # Read the entire config file
        cmd = f"cat {nginx_config}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        full_config = stdout.read().decode()
        
        # Find all server blocks
        lines = full_config.split('\n')
        in_https_server = False
        in_http_server = False
        current_server = None
        
        for i, line in enumerate(lines, 1):
            if 'listen 443' in line and '#' not in line[:line.find('listen')]:
                in_https_server = True
                current_server = 'HTTPS (443)'
                print(f"Line {i}: Found {current_server} server block")
            elif 'listen 80' in line and '#' not in line[:line.find('listen')]:
                in_http_server = True
                current_server = 'HTTP (80)'
                print(f"Line {i}: Found {current_server} server block")
            elif line.strip().startswith('server {'):
                if 'listen 443' not in '\n'.join(lines[max(0, i-5):i]):
                    in_https_server = False
                    in_http_server = False
                    current_server = None
            elif 'location /vidgenerator' in line and not line.strip().startswith('#'):
                if in_https_server:
                    print(f"  Line {i}: [HTTPS] {line.strip()}")
                elif in_http_server:
                    print(f"  Line {i}: [HTTP] {line.strip()}")
                else:
                    print(f"  Line {i}: [UNKNOWN] {line.strip()}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    find_blocks()
