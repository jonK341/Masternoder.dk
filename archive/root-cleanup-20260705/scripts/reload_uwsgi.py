"""
Reload uwsgi using touch method
"""
import paramiko
import os
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def reload():
    """Reload uwsgi"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        
        print("Reloading uwsgi by touching ini file...")
        stdin, stdout, stderr = ssh.exec_command('touch /var/www/html/vidgenerator/uwsgi.ini && systemctl reload uwsgi-vidgenerator.service 2>&1')
        result = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        if result:
            print(result)
        if error:
            print(error)
        
        print("\nWaiting 5 seconds...")
        time.sleep(5)
        
        print("[OK] Reload complete")
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")

if __name__ == "__main__":
    reload()

