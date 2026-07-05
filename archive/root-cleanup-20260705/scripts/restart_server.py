#!/usr/bin/env python3
"""
Restart uWSGI Service to Activate New API Routes
"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

def restart_uwsgi():
    """Restart uWSGI service"""
    print("="*80)
    print("RESTARTING uWSGI SERVICE")
    print("="*80)
    print()
    
    # Connect to server
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {SERVER_HOST}...")
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASSWORD, timeout=30)
        print("[OK] Connected successfully")
        print()
    except Exception as e:
        print(f"[FAIL] Connection failed: {e}")
        return False
    
    try:
        # Check current status
        print("1. Checking current uWSGI status...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi --no-pager")
        status_output = stdout.read().decode('utf-8', errors='ignore')
        print(status_output[:500])
        print()
        
        # Restart uWSGI
        print("2. Restarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("[OK] Restart command executed")
        else:
            error_output = stderr.read().decode('utf-8', errors='ignore')
            print(f"[WARN] Restart returned exit code {exit_status}")
            if error_output:
                print(f"Error: {error_output}")
        
        # Wait for service to restart
        print()
        print("3. Waiting for service to restart (5 seconds)...")
        time.sleep(5)
        
        # Check new status
        print()
        print("4. Checking uWSGI status after restart...")
        stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi --no-pager")
        status_output = stdout.read().decode('utf-8', errors='ignore')
        print(status_output[:500])
        
        # Check if service is active
        stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi")
        is_active = stdout.read().decode('utf-8', errors='ignore').strip()
        
        print()
        print("="*80)
        if is_active == 'active':
            print("[OK] uWSGI service is ACTIVE")
            print("[OK] Service restart successful")
        else:
            print(f"[WARN] uWSGI service status: {is_active}")
            print("[WARN] Service may need additional attention")
        
        print("="*80)
        return is_active == 'active'
        
    except Exception as e:
        print(f"[ERROR] Error during restart: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh.close()

if __name__ == '__main__':
    success = restart_uwsgi()
    sys.exit(0 if success else 1)
