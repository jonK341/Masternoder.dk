#!/usr/bin/env python3
"""
Restart Flask/uWSGI and Apache services
"""
import paramiko
import sys

# Server credentials
SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def restart_services():
    """Restart uWSGI and Apache services"""
    print("=" * 60)
    print("Restarting Services")
    print("=" * 60)
    print()
    
    # Connect to server
    print(f"Connecting to {SERVER_HOST}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD)
        print("Connected!")
    except Exception as e:
        print(f"ERROR: Failed to connect: {e}")
        sys.exit(1)
    
    try:
        commands = [
            ('systemctl restart uwsgi-vidgenerator.service', 'uWSGI service'),
            ('systemctl status uwsgi-vidgenerator.service --no-pager -l | head -20', 'uWSGI status'),
            ('systemctl restart apache2.service', 'Apache service'),
            ('systemctl status apache2.service --no-pager -l | head -20', 'Apache status'),
        ]
        
        for cmd, description in commands:
            try:
                print(f"\n{description}...")
                stdin, stdout, stderr = ssh.exec_command(cmd)
                output = stdout.read().decode('utf-8', errors='replace')
                error_output = stderr.read().decode('utf-8', errors='replace')
                if output:
                    print(output)
                if error_output and 'Failed' not in description and 'charmap' not in str(error_output):
                    print(f"  [WARN] {error_output[:200]}")
            except Exception as e:
                print(f"  [WARN] {cmd}: {e}")
        
        print("\n" + "=" * 60)
        print("SERVICES RESTARTED!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR during restart: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh.close()
        print("\nDisconnected from server")

import os
if __name__ == '__main__':
    restart_services()
