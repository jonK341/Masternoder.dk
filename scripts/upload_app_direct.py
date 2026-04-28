#!/usr/bin/env python3
"""
Directly upload src/app.py to server
"""

import paramiko
import os

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
REMOTE_PATH = "/var/www/html/vidgenerator"
LOCAL_FILE = "src/app.py"

def upload_app():
    """Upload app.py directly"""
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
        print("Uploading src/app.py directly")
        print("=" * 60)
        print()
        
        # Use SCP to upload
        sftp = ssh_client.open_sftp()
        
        # Create remote directory if needed
        remote_dir = f"{REMOTE_PATH}/src"
        try:
            sftp.mkdir(remote_dir)
        except:
            pass  # Directory exists
        
        # Upload file
        remote_file = f"{REMOTE_PATH}/{LOCAL_FILE}"
        print(f"Uploading {LOCAL_FILE} to {remote_file}...")
        sftp.put(LOCAL_FILE, remote_file)
        sftp.close()
        
        print("✅ File uploaded!")
        
        # Verify
        print("\nVerifying upload...")
        cmd = f"grep -n 'register_all_blueprints' {remote_file}"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        output = stdout.read().decode()
        
        if output:
            print("✅ Backend registration code found:")
            print(output[:200])
        else:
            print("❌ Code still not found!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    upload_app()

