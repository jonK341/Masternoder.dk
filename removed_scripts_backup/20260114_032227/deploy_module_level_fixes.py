#!/usr/bin/env python3
"""Deploy fixes for module-level print statements"""
import os
import sys
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

def clear_python_cache(ssh_client):
    """Clear Python cache"""
    print("Clearing Python cache...")
    try:
        ssh_client.exec_command(f"find {REMOTE_PATH} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null")
        ssh_client.exec_command(f"find {REMOTE_PATH} -name '*.pyc' -delete 2>/dev/null")
        print("✅ Cache cleared")
    except Exception as e:
        print(f"⚠️  Error clearing cache: {str(e)}")

def main():
    ssh_client = None
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        
        print("=" * 70)
        print("DEPLOYING MODULE-LEVEL PRINT FIXES")
        print("=" * 70)
        
        # Deploy fixed files
        files_to_deploy = [
            ("src/app.py", f"{REMOTE_PATH}/src/app.py"),
            ("src/web/routes.py", f"{REMOTE_PATH}/src/web/routes.py"),
        ]
        
        sftp = ssh_client.open_sftp()
        for local_file, remote_file in files_to_deploy:
            if os.path.exists(local_file):
                print(f"\nDeploying {local_file}...")
                sftp.put(local_file, remote_file)
                print(f"✅ Deployed")
            else:
                print(f"⚠️  {local_file} not found locally")
        sftp.close()
        
        # Clear Python cache
        print("\n" + "=" * 70)
        clear_python_cache(ssh_client)
        
        # Restart uWSGI
        print("\n" + "=" * 70)
        print("RESTARTING UWSGI")
        print("=" * 70)
        stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi")
        stdout.channel.recv_exit_status()
        print("✅ uWSGI restarted")
        
        # Wait and check status
        import time
        time.sleep(3)
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

