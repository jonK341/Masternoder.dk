"""
Restart Flask service to reload routes
"""
import paramiko
import os
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def restart_services():
    """Restart Flask-related services"""
    try:
        print("=" * 70)
        print("RESTARTING FLASK SERVICES")
        print("=" * 70)
        
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected to server")
        print()
        
        # Find Flask/uWSGI service
        print("Finding Flask/uWSGI service...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command('systemctl list-units --type=service | grep -i "uwsgi\\|flask\\|vidgenerator"')
        services = stdout.read().decode('utf-8', errors='replace')
        print(services)
        print()
        
        # Check uwsgi processes
        print("Checking uwsgi processes...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command('ps aux | grep -i uwsgi | grep -v grep')
        processes = stdout.read().decode('utf-8', errors='replace')
        if processes:
            print(processes)
        else:
            print("[INFO] No uwsgi processes found")
        print()
        
        # Try to restart uwsgi service
        print("Restarting uwsgi service...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command('systemctl stop uwsgi-vidgenerator 2>&1')
        xtdin, stdout, stderr = ssh.exec_command('systemctl start uwsgi-vidgenerator 2>&1')
        result = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        if result:
            print(result)
        if error and "Failed" not in error:
            print(f"[INFO] {error}")
        
        time.sleep(2)
        
        # Check status
        print("\nChecking uwsgi status...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command('systemctl status uwsgi --no-pager -l | head -20')
        status = stdout.read().decode('utf-8', errors='replace')
        print(status)
        print()
        
        # Also restart python-proxy to be safe
        print("Restarting python-proxy service...")
        print("-" * 70)
        stdin, stdout, stderr = ssh.exec_command('systemctl restart python-proxy.service 2>&1')
        result = stdout.read().decode('utf-8', errors='replace')
        print(result)
        print()
        
        time.sleep(2)
        
        print("[OK] Services restarted. Waiting 3 seconds for startup...")
        time.sleep(3)
        print()
        print("=" * 70)
        ssh.close()
        
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    restart_services()

