#!/usr/bin/env python3
"""
Check Duplicate File
Checks if there's a duplicate file at the error path
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_file():
    """Check for duplicate file"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        # Check both paths
        paths = [
            "/var/www/html/backend/services/unified_point_system_json_storage.py",
            "/var/www/html/vidgenerator/backend/services/unified_point_system_json_storage.py",
        ]
        
        for path in paths:
            print(f"\nChecking: {path}")
            # Check if file exists
            stdin, stdout, stderr = ssh.exec_command(f"test -f {path} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
            exists = stdout.read().decode().strip()
            print(f"  Exists: {exists}")
            
            if exists == 'EXISTS':
                # Check what it exports
                stdin, stdout, stderr = ssh.exec_command(f"grep -E '^unified_point|^# Global' {path} | tail -3", timeout=5)
                exports = stdout.read().decode().strip()
                print(f"  Exports: {exports}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    check_file()
