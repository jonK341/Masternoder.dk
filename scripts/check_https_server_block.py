#!/usr/bin/env python3
"""
Check HTTPS Server Block
Checks the actual structure of HTTPS server block
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_block():
    """Check HTTPS server block"""
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
        
        # Find HTTPS server block and show it
        print("Finding HTTPS server block...")
        print()
        in_https = False
        brace_count = 0
        
        for i, line in enumerate(lines):
            if 'listen 443' in line and 'ssl' in line and not line.strip().startswith('#'):
                in_https = True
                brace_count = line.count('{') - line.count('}')
                print(f"Line {i+1}: {line}")
                continue
            
            if in_https:
                brace_count += line.count('{')
                brace_count -= line.count('}')
                print(f"Line {i+1}: {line}")
                if brace_count == 0:
                    print()
                    print(f"HTTPS server block ends at line {i+1}")
                    break
        
        # Also check what comes before and after
        print()
        print("="*70)
        print("Lines around HTTPS server block:")
        print("="*70)
        for i in range(60, min(75, len(lines))):
            print(f"{i+1:4d}: {lines[i]}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_block()
