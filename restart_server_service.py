#!/usr/bin/env python3
"""
Restart Flask service on masternoder.dk server
"""

import paramiko
import sys

# Server credentials
SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def restart_service():
    """Restart Flask service on server"""
    print("=" * 60)
    print("Restarting Flask service on masternoder.dk")
    print("=" * 60)
    print()
    
    # Create SSH client
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("Connecting to server...")
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60,
            look_for_keys=False,
            allow_agent=False
        )
        print("[OK] Connected successfully!")
        print()
        
        # Restart service
        print("Restarting python-proxy.service...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl restart python-proxy.service")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("[OK] Service restarted!")
        else:
            error = stderr.read().decode()
            print(f"[ERROR] Failed to restart service: {error}")
            return False
        
        print()
        
        # Check service status
        print("Checking service status...")
        stdin, stdout, stderr = ssh_client.exec_command("sudo systemctl status python-proxy.service --no-pager | head -5")
        status = stdout.read().decode()
        print(status)
        
        if 'active (running)' in status.lower():
            print("[OK] Service is running!")
        else:
            print("[WARN] Service status unclear")
        
        print()
        print("=" * 60)
        print("[SUCCESS] Service restarted!")
        print("=" * 60)
        print()
        print("Test the site:")
        print("  https://masternoder.dk/vidgenerator")
        print()
        
        return True
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed!")
        return False
    except Exception as e:
        print(f"[ERROR] Failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    success = restart_service()
    sys.exit(0 if success else 1)

import os
