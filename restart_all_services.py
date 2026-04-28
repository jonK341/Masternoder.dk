#!/usr/bin/env python3
"""
Restart all necessary services for UI changes to appear
"""
import paramiko
import os
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def restart_all_services():
    """Restart all services aggressively"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Restarting All Services for UI Changes")
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
        
        # Step 1: Stop all Flask/Python services
        print("Step 1: Stopping all Flask/Python services...")
        stop_commands = [
            "systemctl stop python-proxy.service 2>&1 || true",
            "systemctl stop vidgenerator.service 2>&1 || true",
            "systemctl stop vidgenerator-flask.service 2>&1 || true",
            "systemctl stop flask-vidgenerator.service 2>&1 || true",
            "pkill -f 'python.*run.py' 2>&1 || true",
            "pkill -f 'gunicorn' 2>&1 || true",
            "pkill -f 'uwsgi.*vidgenerator' 2>&1 || true",
        ]
        
        for cmd in stop_commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
            stdout.channel.recv_exit_status()
        
        print("[OK] All services stopped")
        time.sleep(2)
        print()
        
        # Step 2: Clear all caches
        print("Step 2: Clearing all caches...")
        cache_commands = [
            "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
            "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
            "rm -rf /var/www/html/vidgenerator/instance/*.db-journal 2>/dev/null || true",
            "rm -rf /tmp/*.pyc 2>/dev/null || true",
        ]
        
        for cmd in cache_commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=30)
            stdout.channel.recv_exit_status()
        
        print("[OK] Cache cleared")
        print()
        
        # Step 3: Restart python-proxy service
        print("Step 3: Starting python-proxy.service...")
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl start python-proxy.service 2>&1",
            timeout=30
        )
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        if exit_status == 0:
            print("[OK] python-proxy.service started")
        else:
            print(f"[WARN] python-proxy.service start returned: {exit_status}")
            if error:
                print(f"Error: {error[:200]}")
        
        time.sleep(2)
        
        # Then restart it
        print("Restarting python-proxy.service...")
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl restart python-proxy.service 2>&1",
            timeout=30
        )
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] python-proxy.service restarted")
        else:
            print(f"[WARN] Restart status: {exit_status}")
        print()
        
        # Step 4: Restart uWSGI
        print("Step 4: Restarting uWSGI...")
        uwsgi_commands = [
            "systemctl restart uwsgi.service 2>&1 || true",
            "systemctl restart uwsgi 2>&1 || true",
            "service uwsgi restart 2>&1 || true",
        ]
        
        for cmd in uwsgi_commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                output = stdout.read().decode('utf-8', errors='replace')
                if output and 'not found' not in output.lower():
                    print(f"[OK] uWSGI restarted")
                    break
        
        print()
        
        # Step 5: Restart nginx
        print("Step 5: Restarting nginx...")
        nginx_commands = [
            "systemctl restart nginx 2>&1",
            "service nginx restart 2>&1",
        ]
        
        for cmd in nginx_commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print("[OK] nginx restarted")
                break
            else:
                error = stderr.read().decode('utf-8', errors='replace')
                if 'not found' not in error.lower():
                    print(f"[WARN] nginx restart: {error[:100]}")
        
        print()
        
        # Step 6: Wait and verify
        print("Step 6: Waiting for services to stabilize...")
        time.sleep(5)
        
        print("Checking service statuses...")
        
        # Check python-proxy
        stdin, stdout, stderr = ssh_client.exec_command(
            "systemctl is-active python-proxy.service 2>&1",
            timeout=10
        )
        status = stdout.read().decode('utf-8', errors='replace').strip()
        print(f"  python-proxy.service: {status}")
        
        # Check if process is running
        stdin, stdout, stderr = ssh_client.exec_command(
            "ps aux | grep -E 'python.*run.py|gunicorn|uwsgi.*vidgenerator' | grep -v grep | head -n 3",
            timeout=10
        )
        processes = stdout.read().decode('utf-8', errors='replace')
        if processes:
            print("  Running processes found:")
            for line in processes.strip().split('\n')[:3]:
                if line:
                    print(f"    {line[:80]}")
        else:
            print("  [WARN] No Python/Flask processes found")
        
        print()
        print("=" * 70)
        print("[OK] All Services Restarted!")
        print("=" * 70)
        print()
        print("Note: If UI changes don't appear, try:")
        print("  1. Hard refresh browser (Ctrl+Shift+R or Ctrl+F5)")
        print("  2. Clear browser cache")
        print("  3. Check browser console for errors")
        print("  4. Verify file was deployed: backend/routes/game.py")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    success = restart_all_services()
    exit(0 if success else 1)

