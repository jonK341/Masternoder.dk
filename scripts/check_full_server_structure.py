#!/usr/bin/env python3
"""
Check Full Server Structure
Checks the full server block structure
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_structure():
    """Check full server structure"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Read the file
        sftp = ssh.open_sftp()
        with sftp.open(nginx_config, 'r') as f:
            lines = f.read().decode('utf-8').split('\n')
        sftp.close()
        
        # Show all server blocks
        print("All server blocks in config:")
        print("="*70)
        in_server = False
        server_type = None
        brace_count = 0
        
        for i, line in enumerate(lines):
            if 'server {' in line and not line.strip().startswith('#'):
                in_server = True
                brace_count = 1
                if 'listen 443' in '\n'.join(lines[max(0, i-5):i+5]):
                    server_type = 'HTTPS'
                elif 'listen 80' in '\n'.join(lines[max(0, i-5):i+5]):
                    server_type = 'HTTP'
                else:
                    server_type = 'UNKNOWN'
                print(f"\n{server_type} Server Block starts at line {i+1}:")
                print(f"  {line}")
                continue
            
            if in_server:
                brace_count += line.count('{')
                brace_count -= line.count('}')
                if brace_count == 0:
                    print(f"  {line}")
                    print(f"{server_type} Server Block ends at line {i+1}")
                    in_server = False
                    server_type = None
                    continue
                
                # Show key lines
                if any(keyword in line for keyword in ['listen', 'server_name', 'location', 'proxy_pass', 'ssl_certificate']):
                    print(f"  {line}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_structure()
