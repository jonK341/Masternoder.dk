#!/usr/bin/env python3
"""
Read Nginx Config
Reads and displays the nginx configuration
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def read_config():
    """Read nginx config"""
    print("="*70)
    print("READING NGINX CONFIGURATION")
    print("="*70)
    print()
    
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        nginx_config = "/etc/nginx/sites-enabled/masternoder.dk"
        
        # Read config
        sftp = ssh.open_sftp()
        try:
            with sftp.open(nginx_config, 'r') as f:
                config_content = f.read().decode('utf-8')
            
            # Find location blocks for /vidgenerator
            lines = config_content.split('\n')
            in_vidgenerator_block = False
            indent_level = 0
            
            print("Location blocks for /vidgenerator:")
            print()
            for i, line in enumerate(lines):
                if 'location' in line and '/vidgenerator' in line:
                    in_vidgenerator_block = True
                    indent_level = len(line) - len(line.lstrip())
                    print(f"Line {i+1}: {line.strip()}")
                    # Print next 20 lines
                    for j in range(i+1, min(i+21, len(lines))):
                        next_line = lines[j]
                        next_indent = len(next_line) - len(next_line.lstrip())
                        if next_line.strip() and next_indent <= indent_level and 'location' in next_line:
                            break
                        print(f"  {next_line.rstrip()}")
                    print()
        finally:
            sftp.close()
        
        print()
        print("="*70)
        print("CONFIG READING COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    read_config()
