#!/usr/bin/env python3
"""
Restart uWSGI service
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def restart_uwsgi():
    """Restart uWSGI"""
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
        print("Restarting uWSGI")
        print("=" * 60)
        print()
        
        # Find uWSGI process
        cmd = "ps aux | grep uwsgi | grep -v grep"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if output:
            print("Found uWSGI process:")
            print(output)
            print()
            
            # Try to restart uWSGI service
            print("Restarting uWSGI service...")
            cmd2 = "sudo systemctl restart uwsgi || sudo systemctl restart uwsgi.service || sudo service uwsgi restart || echo 'No uwsgi service found'"
            stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
            output2 = stdout2.read().decode()
            error2 = stderr2.read().decode()
            
            if output2:
                print(output2)
            if error2:
                print(error2)
            
            # If no service, kill and restart manually
            if "No uwsgi service found" in output2 or not output2.strip():
                print("No service found, checking for uWSGI config...")
                cmd3 = "find /etc -name '*uwsgi*' -type f 2>/dev/null | head -5"
                stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
                print(stdout3.read().decode())
                
                # Kill uWSGI process
                print("\nKilling uWSGI process...")
                cmd4 = "sudo killall -9 uwsgi 2>/dev/null || pkill -9 uwsgi 2>/dev/null || echo 'No uwsgi process to kill'"
                stdin4, stdout4, stderr4 = ssh_client.exec_command(cmd4)
                print(stdout4.read().decode())
                
                # Check if Flask needs to be restarted via run.py
                print("\nChecking for Flask startup script...")
                cmd5 = "ls -la /var/www/html/vidgenerator/run.py"
                stdin5, stdout5, stderr5 = ssh_client.exec_command(cmd5)
                if stdout5.read().decode().strip():
                    print("Found run.py - Flask should restart automatically")
        else:
            print("❌ No uWSGI process found!")
            print("Flask might be running differently")
        
        print()
        print("Waiting 3 seconds for restart...")
        import time
        time.sleep(3)
        
        # Check if port 5000 is listening
        cmd6 = "netstat -tlnp | grep :5000 || ss -tlnp | grep :5000"
        stdin6, stdout6, stderr6 = ssh_client.exec_command(cmd6)
        output6 = stdout6.read().decode()
        
        if output6:
            print("✅ Port 5000 is listening:")
            print(output6)
        else:
            print("❌ Port 5000 is NOT listening!")
            print("Flask/uWSGI may need manual restart")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    restart_uwsgi()

import os
