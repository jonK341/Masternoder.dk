#!/usr/bin/env python3
"""
Fix Vidgenerator get_top_50
Fixes the get_top_50 call in vidgenerator copy
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix():
    """Fix get_top_50 call"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        file_path = "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py"
        
        # Fix get_top_50(limit=6) -> get_top_50()
        print("Fixing get_top_50 call...")
        cmd = f"sed -i 's/get_top_50(limit=6)/get_top_50()/g' {file_path}"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=5)
        stdout.read()
        print("  [OK] Fixed get_top_50 call")
        
        # Verify
        print()
        print("Verifying fix...")
        cmd2 = f"grep -n 'get_top_50' {file_path} | head -3"
        stdin2, stdout2, stderr2 = ssh.exec_command(cmd2, timeout=5)
        output = stdout2.read().decode().strip()
        print(output)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix()
