#!/usr/bin/env python3
"""
Restart uWSGI service properly
"""

import paramiko
import sys

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def restart_uwsgi_service():
    """Restart uWSGI service"""
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
        print("Restarting uWSGI service")
        print("=" * 60)
        print()
        
        # Check uWSGI service file
        cmd = "cat /etc/systemd/system/uwsgi-vidgenerator.service 2>/dev/null || echo 'Service file not found'"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if "Service file not found" not in output:
            print("Found uWSGI service:")
            print(output)
            print()
            
            # Restart service
            print("Restarting uwsgi-vidgenerator.service...")
            cmd2 = "sudo systemctl restart uwsgi-vidgenerator.service"
            stdin2, stdout2, stderr2 = ssh_client.exec_command(cmd2)
            exit_status = stdout2.channel.recv_exit_status()
            
            if exit_status == 0:
                print("✅ Service restarted!")
            else:
                error = stderr2.read().decode()
                print(f"❌ Failed: {error}")
                
                # Try alternative restart
                print("\nTrying alternative restart method...")
                cmd3 = "cd /var/www/html/vidgenerator && sudo touch uwsgi.ini"
                stdin3, stdout3, stderr3 = ssh_client.exec_command(cmd3)
                print("Touched uwsgi.ini to trigger reload")
        else:
            print("No systemd service found")
            print("Checking uwsgi.ini...")
            cmd4 = "head -20 /var/www/html/vidgenerator/uwsgi.ini"
            stdin4, stdout4, stderr4 = ssh_client.exec_command(cmd4)
            print(stdout4.read().decode())
            
            # Restart by touching ini file (uWSGI auto-reloads)
            print("\nTriggering uWSGI reload...")
            cmd5 = "cd /var/www/html/vidgenerator && sudo touch uwsgi.ini && sleep 2"
            stdin5, stdout5, stderr5 = ssh_client.exec_command(cmd5)
            print("✅ Reload triggered")
        
        print()
        print("Waiting 5 seconds for restart...")
        import time
        time.sleep(5)
        
        # Verify
        cmd6 = "ps aux | grep uwsgi | grep -v grep | wc -l"
        stdin6, stdout6, stderr6 = ssh_client.exec_command(cmd6)
        count = stdout6.read().decode().strip()
        print(f"uWSGI processes: {count}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    restart_uwsgi_service()

import os
