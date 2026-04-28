#!/usr/bin/env python3
"""
Fix Syntax Error
Fixes the syntax error in the vidgenerator copy
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix():
    """Fix syntax error"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        file_path = "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py"
        
        # Fix the backslash issue
        print("Fixing syntax error...")
        cmd = f"sed -i 's/\\\\.get_all_points(/.get_all_points(/g' {file_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
        stdout.read()
        print("  [OK] Fixed backslash issue")
        
        # Verify
        print()
        print("Verifying fix...")
        cmd2 = f"python3 -m py_compile {file_path} 2>&1"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=10)
        output = stdout2.read().decode().strip()
        error = stderr2.read().decode().strip()
        
        if output or error:
            print(f"  [ERROR] Still has syntax error: {output} {error}")
        else:
            print("  [OK] Syntax is correct")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix()
