#!/usr/bin/env python3
"""
Find Flask process
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def find_flask():
    """Find Flask process"""
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
        print("Finding Flask process")
        print("=" * 60)
        print()
        
        # Find Flask/Gunicorn processes
        cmd = "ps aux | grep -E 'flask|gunicorn|run.py|app.py' | grep -v grep"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if output:
            print("Flask processes found:")
            print(output)
        else:
            print("❌ No Flask process found!")
            print("Flask might be running through Gunicorn or another WSGI server")
        
        print()
        
        # Check what's listening on port 5000
        cmd2 = "netstat -tlnp | grep :5000 || ss -tlnp | grep :5000"
        stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
        output2 = stdout2.read().decode()
        
        if output2:
            print("Port 5000 listeners:")
            print(output2)
        else:
            print("❌ Nothing listening on port 5000!")
        
        # Check python_proxy_server.py to see what it's proxying to
        print()
        print("Checking proxy server configuration...")
        cmd3 = "head -50 /var/www/html/vidgenerator/python_proxy_server.py | grep -E 'proxy|5000|flask|app'"
        stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
        output3 = stdout3.read().decode()
        if output3:
            print(output3)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    find_flask()

import os
