#!/usr/bin/env python3
"""
Download only the vidgenerator directory from masternoder.dk
"""
import os
import sys
import paramiko
from scp import SCPClient
from pathlib import Path

# Server credentials
SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
REMOTE_PATH = "/var/www/html/vidgenerator"
LOCAL_PATH = "./server_backup/html/vidgenerator"

def create_local_directory():
    """Create local directory if it doesn't exist"""
    local_dir = Path(LOCAL_PATH)
    local_dir.mkdir(parents=True, exist_ok=True)
    print(f"[OK] Created/verified local directory: {local_dir.absolute()}")
    return local_dir

def copy_vidgenerator():
    """Copy vidgenerator directory from remote server"""
    print("=" * 50)
    print("Downloading vidgenerator directory only")
    print("=" * 50)
    print()
    print(f"Server: {SERVER_HOST}")
    print(f"Username: {USERNAME}")
    print(f"Remote Path: {REMOTE_PATH}")
    print(f"Local Path: {LOCAL_PATH}")
    print()
    
    # Create local directory
    local_dir = create_local_directory()
    
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
        
        # Check if remote directory exists
        stdin, stdout, stderr = ssh_client.exec_command(f"test -d {REMOTE_PATH} && echo 'exists' || echo 'not found'")
        result = stdout.read().decode().strip()
        
        if result != 'exists':
            print(f"[ERROR] Directory {REMOTE_PATH} not found on server!")
            return False
        
        print(f"[OK] Remote directory exists")
        print()
        
        # Create SCP client with increased timeout and progress callback
        print("Starting file copy...")
        print("This may take a while depending on file size...")
        print()
        
        def progress(filename, size, sent):
            """Progress callback for file transfer"""
            if size > 0:
                percent = (sent / size * 100)
                sys.stdout.write(f"\r  Copying: {filename[:50]}... ({percent:.1f}%)")
                sys.stdout.flush()
        
        with SCPClient(
            ssh_client.get_transport(),
            socket_timeout=600,  # 10 minutes timeout
            progress=progress
        ) as scp:
            # Copy directory recursively
            scp.get(REMOTE_PATH, local_path=str(local_dir.parent), recursive=True)
        
        print()
        print()
        print("=" * 50)
        print("[SUCCESS] vidgenerator directory copied successfully!")
        print("=" * 50)
        print()
        
        # Show summary
        file_count = sum(1 for _ in local_dir.rglob('*') if _.is_file())
        dir_count = sum(1 for _ in local_dir.rglob('*') if _.is_dir())
        
        print(f"Summary:")
        print(f"  Files copied: {file_count}")
        print(f"  Directories: {dir_count}")
        print(f"  Location: {local_dir.absolute()}")
        
        return True
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed! Check username and password.")
        return False
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH error: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

def main():
    """Main function"""
    try:
        success = copy_vidgenerator()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nCopy cancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()

