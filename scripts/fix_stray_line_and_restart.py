#!/usr/bin/env python3
"""
Fix Stray Line and Restart
Fixes the stray line in register_blueprints.py and restarts uWSGI
"""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def fix_and_restart():
    """Fix and restart"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        register_file = '/var/www/html/vidgenerator/backend/register_blueprints.py'
        
        # Read and fix
        print("[1/4] Reading and fixing file...")
        sftp = ssh.open_sftp()
        with sftp.open(register_file, 'r') as f:
            lines = f.read().decode('utf-8').split('\n')
        
        # Fix line 2345 - remove stray line
        if len(lines) > 2344 and 'point_analytics_routes' in lines[2344]:
            print("  Removing stray line at 2345...")
            lines.pop(2344)  # Remove the stray line
        
        new_content = '\n'.join(lines)
        with sftp.open(register_file, 'w') as f:
            f.write(new_content.encode('utf-8'))
        sftp.close()
        print("  ✅ File fixed")
        
        # Test syntax
        print()
        print("[2/4] Testing syntax...")
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
        
        # Clear cache
        print()
        print("[3/4] Clearing cache...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null; echo 'Done'",
            timeout=30
        )
        stdout2.read()
        print("  [OK] Cache cleared")
        
        # Restart uWSGI (non-blocking)
        print()
        print("[4/4] Restarting uWSGI...")
        stdin3, stdout3, stderr3 = ssh.exec_command(
            "systemctl restart uwsgi-vidgenerator.service &",
            timeout=5
        )
        print("  [OK] Restart command sent")
        
        # Wait and check status
        time.sleep(8)
        stdin4, stdout4, stderr4 = ssh.exec_command(
            "systemctl is-active uwsgi-vidgenerator.service",
            timeout=5
        )
        status = stdout4.read().decode().strip()
        print(f"  Status: {status}")
        
        print()
        print("="*70)
        print("FIX AND RESTART COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    fix_and_restart()
