#!/usr/bin/env python3
"""
Check Server Tech Tree File
Reads the actual file on the server around line 188
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_file():
    """Check file"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        tech_tree_file = '/var/www/html/vidgenerator/backend/routes/tech_tree_routes.py'
        
        # Read file around line 188
        print("[1/2] Reading file around line 188...")
        sftp = ssh.open_sftp()
        with sftp.open(tech_tree_file, 'r') as f:
            lines = f.readlines()
        sftp.close()
        
        print(f"Total lines: {len(lines)}")
        print()
        print("Lines 180-200:")
        for i in range(max(0, 179), min(len(lines), 200)):
            marker = ">>>" if i == 187 else "   "
            print(f"{marker} {i+1:3d}: {lines[i].rstrip()}")
        
        # Test syntax
        print()
        print("[2/2] Testing syntax...")
        stdin, stdout, stderr = ssh.exec_command(
            f"python3 -m py_compile {tech_tree_file} 2>&1",
            timeout=10
        )
        error = stderr.read().decode().strip()
        if error:
            print(f"  ❌ Syntax error: {error}")
        else:
            print("  ✅ Syntax is valid")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_file()
