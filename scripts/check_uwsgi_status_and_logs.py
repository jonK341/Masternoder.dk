#!/usr/bin/env python3
"""
Check uWSGI Status and Logs
Checks uWSGI status and recent error logs
"""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def check_status():
    """Check status"""
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("[OK] Connected to server")
        print()
        
        # Check uWSGI status
        print("[1/3] Checking uWSGI status...")
        stdin, stdout, stderr = ssh.exec_command(
            "systemctl status uwsgi-vidgenerator.service --no-pager | head -15",
            timeout=10
        )
        status = stdout.read().decode().strip()
        print(status)
        
        # Check if it's listening
        print()
        print("[2/3] Checking if uWSGI is listening...")
        stdin2, stdout2, stderr2 = ssh.exec_command(
            "netstat -tlnp 2>/dev/null | grep 5000 || ss -tlnp 2>/dev/null | grep 5000",
            timeout=5
        )
        listening = stdout2.read().decode().strip()
        if listening:
            print(f"  ✅ uWSGI is listening:")
            print(f"    {listening}")
        else:
            print("  ❌ uWSGI is NOT listening on port 5000")
        
        # Check recent errors
        print()
        print("[3/3] Checking recent uWSGI errors...")
        stdin3, stdout3, stderr3 = ssh.exec_command(
            "tail -50 /var/www/html/vidgenerator/uwsgi.log | grep -i 'error\\|traceback\\|failed' | tail -20",
            timeout=5
        )
        errors = stdout3.read().decode().strip()
        if errors:
            print("  Recent errors:")
            print(errors)
        else:
            print("  ✅ No recent errors found")
        
        # Check if app started successfully
        print()
        print("Checking if app started...")
        stdin4, stdout4, stderr4 = ssh.exec_command(
            "tail -100 /var/www/html/vidgenerator/uwsgi.log | grep -i 'app.*started\\|application.*ready\\|uwsgi.*ready' | tail -5",
            timeout=5
        )
        startup = stdout4.read().decode().strip()
        if startup:
            print("  Startup messages:")
            print(startup)
        
        ssh.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_status()
