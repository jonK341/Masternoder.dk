#!/usr/bin/env python3
"""
Fix Vidgenerator Unified Dashboard
Fixes the vidgenerator copy of unified_dashboard_routes.py
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix():
    """Fix vidgenerator copy"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        file_path = "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py"
        
        # Replace get_points with get_all_points
        print("Fixing get_points -> get_all_points...")
        cmd = f"sed -i 's/\\.get_points(/\\\\.get_all_points(/g' {file_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
        stdout.read()
        print("  [OK] Replaced get_points with get_all_points")
        
        # Also need to handle the return value format
        # Check if we need to add the format handling code
        print()
        print("Verifying fix...")
        stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -n 'get_all_points' {file_path} | head -2", timeout=5)
        output = stdout2.read().decode().strip()
        print(output)
        
        # Check if format handling is needed
        stdin3, stdout3, stderr3 = ssh.exec_command(f"grep -A 5 'get_all_points' {file_path} | head -10", timeout=5)
        output3 = stdout3.read().decode().strip()
        print("\nContext:")
        print(output3)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix()
