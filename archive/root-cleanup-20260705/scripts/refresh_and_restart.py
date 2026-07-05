#!/usr/bin/env python3
"""
Refresh cache and restart all services
"""
import paramiko
import os
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def refresh_and_restart():
    """Refresh cache and restart services"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Refresh Cache and Restart Services")
        print("=" * 70)
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("[OK] Connected!")
        print()
        
        # Step 1: Clear cache
        print("Step 1: Clearing cache...")
        cache_commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            "rm -rf /var/www/html/vidgenerator/instance/*.db-journal 2>/dev/null || true",
            "systemctl reload nginx 2>/dev/null || true",
        ]
        
        for cmd in cache_commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=30)
            stdout.channel.recv_exit_status()
        
        print("[OK] Cache cleared")
        print()
        
        # Step 2: Restart python-proxy service (Flask)
        print("Step 2: Restarting python-proxy.service (Flask)...")
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl restart python-proxy.service",
            timeout=30
        )
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] python-proxy.service restarted")
        else:
            error = stderr.read().decode('utf-8', errors='replace')
            print(f"[WARN] python-proxy.service restart status: {exit_status}")
            if error:
                print(f"Error: {error[:200]}")
        print()
        
        # Step 3: Restart uWSGI if present
        print("Step 3: Checking for uWSGI service...")
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl list-units --type=service | grep -i uwsgi || echo 'No uwsgi service'",
            timeout=10
        )
        output = stdout.read().decode('utf-8', errors='replace')
        if 'uwsgi' in output.lower() and 'No uwsgi service' not in output:
            print("Restarting uWSGI service...")
            stdin, stdout, stderr = ssh_client.exec_command(
                "systemctl restart uwsgi.service 2>&1 || systemctl restart uwsgi 2>&1",
                timeout=10
            )
            stdout.channel.recv_exit_status()
            print("[OK] uWSGI service restarted")
        else:
            print("[INFO] No uWSGI service found")
        print()
        
        # Step 4: Restart nginx
        print("Step 4: Restarting nginx...")
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl restart nginx 2>&1 || service nginx restart 2>&1",
            timeout=10
        )
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] nginx restarted")
        else:
            print(f"[WARN] nginx restart status: {exit_status}")
        print()
        
        # Step 5: Wait and check service status
        print("Step 5: Waiting for services to start...")
        time.sleep(3)
        
        print("Checking service status...")
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl is-active python-proxy.service 2>&1",
            timeout=10
        )
        status = stdout.read().decode('utf-8', errors='replace').strip()
        if status == 'active':
            print("[OK] python-proxy.service is active")
        else:
            print(f"[WARN] python-proxy.service status: {status}")
        
        print()
        print("=" * 70)
        print("[OK] Refresh and Restart Complete!")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    success = refresh_and_restart()
    exit(0 if success else 1)

