#!/usr/bin/env python3
"""
Fix Vidgenerator Unified Dashboard Complete
Fixes all method calls in the vidgenerator copy
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix():
    """Fix all method calls"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        file_path = "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py"
        
        # Fix get_points -> get_all_points (if not already fixed)
        print("Fixing method calls...")
        cmd1 = f"sed -i 's/\\.get_points(/.get_all_points(/g' {file_path}"
        stdin1, stdout1, stderr1 = ssh.exec_command(cmd1, timeout=5)
        stdout1.read()
        print("  [OK] Fixed get_points -> get_all_points")
        
        # Fix get_energy -> get_energy_status
        cmd2 = f"sed -i 's/\\.get_energy(user_id)/.get_energy_status(user_id)/g' {file_path}"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=5)
        stdout2.read()
        print("  [OK] Fixed get_energy -> get_energy_status")
        
        # Verify syntax
        print()
        print("Verifying syntax...")
        cmd3 = f"python3 -m py_compile {file_path} 2>&1"
        stdin3, stdout3, stderr3 = ssh.exec_command(cmd3, timeout=10)
        output = stdout3.read().decode().strip()
        error = stderr3.read().decode().strip()
        
        if output or error:
            print(f"  [ERROR] Syntax error: {output} {error}")
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
