#!/usr/bin/env python3
"""
Verify Server File
Verifies that the fix is on the server
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def verify():
    """Verify file on server"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        file_path = "/var/www/html/backend/routes/unified_dashboard_routes.py"
        
        # Check for get_all_points
        cmd = f"grep -n 'get_all_points' {file_path} | head -3"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
        output = stdout.read().decode().strip()
        print("get_all_points usage:")
        print(output)
        
        # Check for get_points (should not exist)
        cmd2 = f"grep -n 'get_points' {file_path} | grep -v 'get_all_points' | head -3"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=5)
        output2 = stdout2.read().decode().strip()
        if output2:
            print("\nWARNING: Found get_points (should be get_all_points):")
            print(output2)
        else:
            print("\n[OK] No get_points found (correct)")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    verify()
