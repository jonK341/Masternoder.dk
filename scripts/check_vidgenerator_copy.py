#!/usr/bin/env python3
"""
Check Vidgenerator Copy
Checks if there's a vidgenerator copy of unified_dashboard_routes.py
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check():
    """Check vidgenerator copy"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        
        paths = [
            "/var/www/html/backend/routes/unified_dashboard_routes.py",
            "/var/www/html/vidgenerator/backend/routes/unified_dashboard_routes.py",
        ]
        
        for path in paths:
            print(f"\nChecking: {path}")
            stdin, stdout, stderr = ssh.exec_command(f"test -f {path} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
            exists = stdout.read().decode().strip()
            print(f"  Exists: {exists}")
            
            if exists == 'EXISTS':
                # Check for get_all_points
                stdin2, stdout2, stderr2 = ssh.exec_command(f"grep -n 'get_all_points' {path} | head -2", timeout=5)
                output = stdout2.read().decode().strip()
                if output:
                    print(f"  Uses get_all_points: {output}")
                else:
                    print("  [WARN] Does not use get_all_points")
                
                # Check for get_points
                stdin3, stdout3, stderr3 = ssh.exec_command(f"grep -n '\.get_points(' {path} | head -2", timeout=5)
                output3 = stdout3.read().decode().strip()
                if output3:
                    print(f"  [ERROR] Still uses get_points: {output3}")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    check()
