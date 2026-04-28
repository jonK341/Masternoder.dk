#!/usr/bin/env python3
"""
Clear Python Cache
Clears Python bytecode cache and restarts uwsgi
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def clear_cache():
    """Clear Python cache"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Find and remove .pyc files
        print("Clearing Python cache...")
        cmd = "find /var/www/html -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; find /var/www/html -name '*.pyc' -delete 2>/dev/null; echo 'Cache cleared'"
        stdin, stdout, stderr = ssh.exec_command(cmd, timeout=30)
        output = stdout.read().decode().strip()
        print(output)
        
        # Restart uwsgi
        print()
        print("Restarting uwsgi...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator", timeout=10)
        stdout.read()  # Wait
        print("  [OK] uwsgi restarted")
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    clear_cache()
