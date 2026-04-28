#!/usr/bin/env python3
"""
Upload rettigheder files directly to server
"""

import paramiko
import os

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
REMOTE_PATH = "/var/www/html/vidgenerator"

def upload_files():
    """Upload rettigheder files"""
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
        print("Uploading Rettigheder Files")
        print("=" * 60)
        print()
        
        sftp = ssh_client.open_sftp()
        
        files_to_upload = [
            ("backend/routes/rettigheder.py", f"{REMOTE_PATH}/backend/routes/rettigheder.py"),
            ("backend/templates/api_debugger.html", f"{REMOTE_PATH}/backend/templates/api_debugger.html"),
            ("backend/register_blueprints.py", f"{REMOTE_PATH}/backend/register_blueprints.py"),
        ]
        
        for local_file, remote_file in files_to_upload:
            if not os.path.exists(local_file):
                print(f"❌ {local_file} not found locally!")
                continue
            
            # Create remote directory if needed
            remote_dir = os.path.dirname(remote_file)
            try:
                sftp.mkdir(remote_dir)
            except:
                pass  # Directory exists
            
            print(f"Uploading {local_file}...")
            sftp.put(local_file, remote_file)
            print(f"✅ {local_file} uploaded!")
        
        sftp.close()
        
        print()
        print("✅ All files uploaded!")
        
        # Verify
        print("\nVerifying upload...")
        cmd = f"test -f {REMOTE_PATH}/backend/routes/rettigheder.py && echo 'EXISTS' || echo 'MISSING'"
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        status = stdout.read().decode().strip()
        print(f"Rettigheder file: {status}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == '__main__':
    upload_files()

