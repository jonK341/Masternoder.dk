#!/usr/bin/env python3
"""
Check uWSGI Logs
Checks uwsgi logs for recent errors
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_logs():
    """Check uwsgi logs"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        log_path = "/var/www/html/vidgenerator/uwsgi.log"
        
        print("Checking last 50 lines of uwsgi.log...")
        print()
        stdin, stdout, stderr = ssh.exec_command(f"tail -50 {log_path} 2>&1", timeout=10)
        output = stdout.read().decode().strip()
        if output:
            print(output)
        else:
            print("  [WARN] No output from log file")
        
        print()
        print("="*70)
        print("LOG CHECK COMPLETE")
        print("="*70)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_logs()
