#!/usr/bin/env python3
"""
Robust uWSGI restart with timeout handling
"""

import paramiko
import time

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def restart_robust():
    """Restart uWSGI with better error handling"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        
        print("=" * 60)
        print("Restarting uWSGI (Robust Method)")
        print("=" * 60)
        print()
        
        # Method 1: Systemctl restart
        print("Method 1: systemctl restart...")
        cmd1 = "sudo systemctl restart uwsgi-vidgenerator.service"
        stdin1, stdout1, stderr1 = ssh_client.exec_command(cmd1, timeout=10)
        
        # Don't wait for exit status, just start it
        time.sleep(2)
        
        # Method 2: Touch uwsgi.ini to trigger reload
        print("Method 2: Touch uwsgi.ini for reload...")
        cmd2 = "cd /var/www/html/vidgenerator && sudo touch uwsgi.ini 2>/dev/null || true"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2, timeout=5)
        stdout2.channel.recv_exit_status()
        
        print("✅ Restart commands sent")
        print()
        print("Waiting 8 seconds for restart...")
        time.sleep(8)
        
        # Verify
        print("\nVerifying uWSGI status...")
        cmd3 = "ps aux | grep '[u]wsgi' | wc -l"
        stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3, timeout=5)
        count = stdout3.read().decode().strip()
        print(f"uWSGI processes: {count}")
        
        # Check service status
        cmd4 = "sudo systemctl is-active uwsgi-vidgenerator.service 2>/dev/null || echo 'unknown'"
        stdin4, stdout4, stderr4 = ssh_client.exec_command(cmd4, timeout=5)
        status = stdout4.read().decode().strip()
        print(f"Service status: {status}")
        
        print()
        print("✅ Restart complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    restart_robust()

import os
