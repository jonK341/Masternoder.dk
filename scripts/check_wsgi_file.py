#!/usr/bin/env python3
"""
Check WSGI File
Checks what wsgi.py file uWSGI is using
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_wsgi():
    """Check wsgi file"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        wsgi_paths = [
            "/var/www/html/vidgenerator/wsgi.py",
            "/var/www/html/wsgi.py",
            "/var/www/html/src/wsgi.py"
        ]
        
        for wsgi_path in wsgi_paths:
            print(f"Checking: {wsgi_path}")
            stdin, stdout, stderr = ssh.exec_command(f"test -f {wsgi_path} && echo 'EXISTS' || echo 'NOT FOUND'", timeout=5)
            exists = stdout.read().decode().strip()
            
            if exists == 'EXISTS':
                print(f"  ✅ File exists")
                # Read first 50 lines
                stdin2, stdout2, stderr2 = ssh.exec_command(f"head -50 {wsgi_path}", timeout=5)
                content = stdout2.read().decode().strip()
                print(f"  Content (first 50 lines):")
                print("-" * 70)
                print(content)
                print("-" * 70)
            else:
                print(f"  ❌ File not found")
            print()
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_wsgi()
