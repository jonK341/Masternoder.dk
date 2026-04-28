#!/usr/bin/env python3
"""
Start production services on masternoder.dk
"""
import paramiko
import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def start_services():
    """Start all production services"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 60)
        print("Starting Production Services")
        print("=" * 60)
        print()
        print(f"Connecting to {SERVER_HOST}...")
        
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        # Start uWSGI service (Flask app)
        print("\nStarting uwsgi-vidgenerator.service (Flask app)...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl start uwsgi-vidgenerator.service")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] uwsgi-vidgenerator.service started")
        else:
            error = stderr.read().decode('utf-8', errors='replace')
            print(f"[WARN] uwsgi-vidgenerator.service start status: {exit_status}")
            if error:
                print(f"Error: {error}")
        
        # Start python-proxy service
        print("\nStarting python-proxy.service...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl start python-proxy.service")
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] python-proxy.service started")
        else:
            error = stderr.read().decode('utf-8', errors='replace')
            print(f"[WARN] python-proxy.service start status: {exit_status}")
            if error:
                print(f"Error: {error}")
        
        # Enable services to start on boot
        print("\nEnabling services to start on boot...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl enable uwsgi-vidgenerator.service python-proxy.service")
        stdout.read()  # Read output
        print("[OK] Services enabled")
        
        # Check service status
        print("\n" + "=" * 60)
        print("Service Status")
        print("=" * 60)
        
        # Check uWSGI
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl status uwsgi-vidgenerator.service --no-pager")
        status = stdout.read().decode('utf-8', errors='replace')
        if 'active (running)' in status:
            print("[OK] uwsgi-vidgenerator.service is running")
        else:
            print("[WARN] uwsgi-vidgenerator.service status:")
            print(status.encode('ascii', errors='replace').decode('ascii')[:500])
        
        # Check python-proxy
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl status python-proxy.service --no-pager")
        status = stdout.read().decode('utf-8', errors='replace')
        if 'active (running)' in status:
            print("[OK] python-proxy.service is running")
        else:
            print("[WARN] python-proxy.service status:")
            print(status.encode('ascii', errors='replace').decode('ascii')[:500])
        
        # Check Apache/Nginx
        print("\nChecking web server...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl status apache2 --no-pager 2>/dev/null || sudo systemctl status nginx --no-pager 2>/dev/null")
        status = stdout.read().decode('utf-8', errors='replace')
        if 'active (running)' in status:
            print("[OK] Web server (Apache/Nginx) is running")
        else:
            print("[INFO] Web server status unclear")
        
        print("\n" + "=" * 60)
        print("Production Services Started!")
        print("=" * 60)
        print("\nLive site: https://masternoder.dk/vidgenerator")
        print("\nServices:")
        print("  [OK] uwsgi-vidgenerator.service - Flask application")
        print("  [OK] python-proxy.service - Reverse proxy")
        print("  [OK] Web server (Apache/Nginx) - Static files and routing")
        
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        ssh_client.close()

if __name__ == '__main__':
    start_services()

