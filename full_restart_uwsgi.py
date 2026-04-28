"""
Full stop/start restart of uwsgi
"""
import paramiko
import os
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def full_restart():
    """Full restart"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        
        print("Stopping uwsgi-vidgenerator.service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl stop uwsgi-vidgenerator.service 2>&1')
        result = stdout.read().decode('utf-8', errors='replace')
        print(result)
        time.sleep(2)
        
        print("\nStarting uwsgi-vidgenerator.service...")
        stdin, stdout, stderr = ssh.exec_command('systemctl start uwsgi-vidgenerator.service 2>&1')
        result = stdout.read().decode('utf-8', errors='replace')
        print(result)
        
        print("\nWaiting 10 seconds for full startup...")
        time.sleep(10)
        
        print("[OK] Full restart complete")
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")

if __name__ == "__main__":
    full_restart()

