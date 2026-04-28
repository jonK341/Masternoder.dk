#!/usr/bin/env python3
"""
Quick upload and activation script
Uploads files via SFTP and restarts services automatically
"""
import os
import sys
import paramiko
from pathlib import Path
from typing import List

SERVER_HOST = "masternoder.dk"
USERNAME = "root"
PASSWORD = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
REMOTE_PATH = "/var/www/html/vidgenerator"
BASE_DIR = Path(__file__).parent.resolve()

def upload_file(ssh_client, local_file: Path, remote_file: str):
    """Upload a single file"""
    try:
        from scp import SCPClient
        with SCPClient(ssh_client.get_transport()) as scp:
            # Create remote directory if needed
            remote_dir = os.path.dirname(remote_file)
            if remote_dir and remote_dir != REMOTE_PATH:
                mkdir_cmd = f"mkdir -p '{remote_dir}'"
                stdin, stdout, stderr = ssh_client.exec_command(mkdir_cmd)
                stdout.channel.recv_exit_status()
            
            # Upload file
            scp.put(str(local_file), remote_file)
            return True
    except Exception as e:
        print(f"  [ERROR] {local_file.name}: {e}")
        return False

def upload_and_activate(files_to_upload: List[str] = None, auto_restart: bool = True):
    """Upload files and activate on server"""
    print("=" * 80)
    print("QUICK UPLOAD AND ACTIVATE")
    print("=" * 80)
    print()
    
    # If no files specified, ask user
    if not files_to_upload:
        print("No files specified. Usage:")
        print("  python quick_upload_and_activate.py backend/routes/stats.py")
        print("  python quick_upload_and_activate.py vidgenerator/index.html")
        print("  python quick_upload_and_activate.py backend/ vidgenerator/")
        print()
        print("Or upload via FileZilla and just activate:")
        print("  python quick_upload_and_activate.py --restart-only")
        print()
        if '--restart-only' in sys.argv:
            files_to_upload = []
        else:
            files_to_upload = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Connect to server
    print("Connecting to server...")
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=30
        )
        print("[OK] Connected")
        print()
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        return False
    
    try:
        # Upload files if specified
        if files_to_upload:
            print("=" * 80)
            print("UPLOADING FILES")
            print("=" * 80)
            
            uploaded = 0
            failed = 0
            
            for file_path in files_to_upload:
                local_path = BASE_DIR / file_path
                
                if not local_path.exists():
                    print(f"[SKIP] {file_path} (not found locally)")
                    continue
                
                # Determine remote path
                remote_file = f"{REMOTE_PATH}/{file_path}".replace("\\", "/")
                
                if local_path.is_file():
                    print(f"Uploading {file_path}...")
                    if upload_file(ssh_client, local_path, remote_file):
                        print(f"  [OK] {file_path}")
                        uploaded += 1
                    else:
                        failed += 1
                elif local_path.is_dir():
                    # Upload all files in directory
                    print(f"Uploading directory {file_path}...")
                    for local_file in local_path.rglob("*"):
                        if local_file.is_file():
                            rel_path = local_file.relative_to(BASE_DIR)
                            remote_file_path = f"{REMOTE_PATH}/{str(rel_path).replace(chr(92), '/')}"
                            if upload_file(ssh_client, local_file, remote_file_path):
                                uploaded += 1
                            else:
                                failed += 1
                    print(f"  [OK] Directory {file_path} ({uploaded} files)")
            
            print()
            print(f"Uploaded: {uploaded}, Failed: {failed}")
            print()
        
        # Activate (restart services)
        if auto_restart:
            print("=" * 80)
            print("ACTIVATING CHANGES (Restarting Services)")
            print("=" * 80)
            
            # Restart uWSGI
            print("Restarting uWSGI...")
            stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi.service")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print("[OK] uWSGI restarted")
            else:
                error = stderr.read().decode()
                print(f"[WARN] {error[:100]}")
            
            # Reload nginx
            print("Reloading nginx...")
            stdin, stdout, stderr = ssh_client.exec_command("systemctl reload nginx")
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print("[OK] Nginx reloaded")
            else:
                error = stderr.read().decode()
                print(f"[WARN] {error[:100]}")
            
            print()
            print("[SUCCESS] Changes activated!")
            print()
            print("Next steps:")
            print("  1. Clear browser cache (Ctrl+Shift+R)")
            print("  2. Hard refresh the page")
            print("  3. Or use incognito mode")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    # Parse command line arguments
    if '--restart-only' in sys.argv:
        files = []
    else:
        files = [f for f in sys.argv[1:] if not f.startswith('--')]
    
    success = upload_and_activate(files)
    sys.exit(0 if success else 1)

