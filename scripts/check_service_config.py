#!/usr/bin/env python3
"""
Check what python-proxy.service is running
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def check_service():
    """Check service configuration"""
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
        print("Checking python-proxy.service configuration")
        print("=" * 60)
        print()
        
        # Check service file
        cmd = "cat /etc/systemd/system/python-proxy.service"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        print("Service configuration:")
        print(output)
        print()
        
        # Check what's running
        cmd2 = "ps aux | grep python | grep -v grep"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        print("Running Python processes:")
        print(stdout2.read().decode())
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    check_service()

import os
