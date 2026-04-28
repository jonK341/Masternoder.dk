#!/usr/bin/env python3
"""
Check Syntax Error
Checks if there's a syntax error in the file
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check():
    """Check syntax"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        file_path = "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py"
        
        # Check Python syntax
        print("Checking Python syntax...")
        cmd = f"python3 -m py_compile {file_path} 2>&1"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        
        if output or error:
            print(f"Syntax error: {output}")
            print(f"Error: {error}")
        else:
            print("  [OK] No syntax errors")
        
        # Check the actual line
        print()
        print("Checking the line...")
        cmd2 = f"sed -n '91p' {file_path}"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=5)
        output2 = stdout2.read().decode().strip()
        print(f"Line 91: {output2}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    check()
