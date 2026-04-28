#!/usr/bin/env python3
"""
Check uWSGI App Module
Checks what app module uWSGI is using
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_module():
    """Check uWSGI app module"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        uwsgi_ini = "/var/www/html/vidgenerator/uwsgi.ini"
        
        print("Checking uWSGI configuration...")
        print()
        
        # Read uwsgi.ini
        sftp = ssh.open_sftp()
        with sftp.open(uwsgi_ini, 'r') as f:
            content = f.read().decode('utf-8')
        sftp.close()
        
        print("uWSGI.ini content:")
        print("-" * 70)
        print(content)
        print("-" * 70)
        
        # Check if module and callable are set
        if 'module' in content or 'wsgi-file' in content:
            print()
            print("✅ uWSGI module configuration found")
        else:
            print()
            print("⚠️  No module/wsgi-file found in uwsgi.ini")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_module()
