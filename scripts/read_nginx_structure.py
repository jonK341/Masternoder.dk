#!/usr/bin/env python3
"""
Read Nginx Structure
Reads nginx config to understand structure
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def read_structure():
    """Read nginx structure"""
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
        
        # Find HTTPS server block boundaries
        https_start = None
        https_end = None
        
        for i, line in enumerate(lines):
            if 'listen 443' in line and 'ssl' in line and not line.strip().startswith('#'):
                https_start = i
                print(f"HTTPS server block starts at line {i+1}: {line.strip()}")
                # Find the closing brace
                brace_count = 0
                for j in range(i, len(lines)):
                    brace_count += lines[j].count('{')
                    brace_count -= lines[j].count('}')
                    if brace_count == 0 and j > i:
                        https_end = j
                        print(f"HTTPS server block ends at line {j+1}: {lines[j].strip()}")
                        break
                break
        
        # Show what's in the HTTPS server block
        if https_start is not None and https_end is not None:
            print()
            print("Content of HTTPS server block:")
            print("-" * 70)
            for i in range(https_start, min(https_end+1, len(lines))):
                print(f"{i+1:4d}: {lines[i]}")
        
        # Find HTTP server block location blocks
        print()
        print("="*70)
        print("Location blocks in HTTP server block (to copy):")
        print("="*70)
        for i, line in enumerate(lines):
            if 'location /vidgenerator' in line and not line.strip().startswith('#'):
                # Print this location block
                j = i
                indent_level = len(line) - len(line.lstrip())
                while j < len(lines):
                    print(f"{j+1:4d}: {lines[j]}")
                    if lines[j].strip() == '}' and len(lines[j]) - len(lines[j].lstrip()) == indent_level:
                        break
                    j += 1
                print()
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    read_structure()
