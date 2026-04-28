#!/usr/bin/env python3
"""
Fix Server Register Blueprints Final
Fixes the register_blueprints.py file on server to match local version
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_final():
    """Fix final"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        
        # Read local file
        print("[1/4] Reading local file...")
        with open('backend/register_blueprints.py', 'r', encoding='utf-8') as f:
            local_content = f.read()
        print(f"  [OK] Read {len(local_content)} bytes from local file")
        
        # Read server file
        print()
        print("[2/4] Reading server file...")
        sftp = ssh.open_sftp()
        with sftp.open(register_file, 'r') as f:
            server_content = f.read().decode('utf-8')
        print(f"  [OK] Read {len(server_content)} bytes from server file")
        
        # Check if they're different around line 2336
        print()
        print("[3/4] Comparing files...")
        local_lines = local_content.split('\n')
        server_lines = server_content.split('\n')
        
        print("Local file (lines 2335-2348):")
        for i in range(2334, min(2348, len(local_lines))):
            print(f"  {i+1:4d}: {local_lines[i]}")
        
        print()
        print("Server file (lines 2335-2348):")
        for i in range(2334, min(2348, len(server_lines))):
            print(f"  {i+1:4d}: {server_lines[i]}")
        
        # Write local file to server
        print()
        print("[4/4] Writing local file to server...")
        with sftp.open(register_file, 'w') as f:
            f.write(local_content.encode('utf-8'))
        sftp.close()
        print("  [OK] File written")
        
        # Test syntax
        print()
        print("Testing syntax...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 -m py_compile {register_file} 2>&1",
            timeout=10
        )
        error = stderr.read().decode().strip()
        if error:
            print(f"  ❌ Syntax error: {error}")
            return False
        else:
            print("  ✅ Syntax is valid")
        
        print()
        print("="*70)
        print("FILE FIXED - READY FOR RESTART")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_final()
