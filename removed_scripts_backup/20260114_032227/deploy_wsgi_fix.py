#!/usr/bin/env python3
"""Deploy wsgi.py fix to suppress output during app creation"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("DEPLOYING WSGI.PY FIX")
        print("=" * 70)
        
        # Read local wsgi.py
        with open('wsgi.py', 'r', encoding='utf-8') as f:
            local_content = f.read()
        
        # Upload to server
        sftp = ssh_client.open_sftp()
        with sftp.file(f'{REMOTE_PATH}/wsgi.py', 'w') as f:
            f.write(local_content)
        sftp.close()
        
        print("✅ wsgi.py deployed")
        
        # Force restart uWSGI
        print("\nForce restarting uWSGI...")
        stdin, stdout, stderr = ssh_client.exec_command("systemctl stop uwsgi && sleep 2 && systemctl start uwsgi")
        stdout.channel.recv_exit_status()
        print("✅ uWSGI restarted")
        
        # Check status
        stdin, stdout, stderr = ssh_client.exec_command("systemctl status uwsgi --no-pager -l | head -15")
        status = stdout.read().decode('utf-8', errors='ignore')
        print("\nStatus:")
        print(status)
        
        print("\n" + "=" * 70)
        print("✅ DEPLOYMENT COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        if ssh_client:
            ssh_client.close()

if __name__ == "__main__":
    main()

