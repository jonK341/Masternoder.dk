#!/usr/bin/env python3
"""
Deploy updated design HTML files to production server
"""
import os
import sys
import paramiko
from pathlib import Path

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    ("vidgenerator/index.html", f"{REMOTE_PATH}/vidgenerator/index.html"),
    ("vidgenerator/debugger/index.html", f"{REMOTE_PATH}/vidgenerator/debugger/index.html"),
    ("vidgenerator/generator/index.html", f"{REMOTE_PATH}/vidgenerator/generator/index.html"),
    ("vidgenerator/gallery/index.html", f"{REMOTE_PATH}/vidgenerator/gallery/index.html"),
    ("vidgenerator/stats/index.html", f"{REMOTE_PATH}/vidgenerator/stats/index.html"),
    ("vidgenerator/game/index.html", f"{REMOTE_PATH}/vidgenerator/game/index.html"),
    ("vidgenerator/static/css/modern-design-system.css", f"{REMOTE_PATH}/vidgenerator/static/css/modern-design-system.css"),
]

def deploy_files():
    """Deploy updated HTML files to server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 80)
        print("DEPLOYING UPDATED DESIGN FILES")
        print("=" * 80)
        print(f"Server: {SERVER_HOST}")
        print(f"Target: {REMOTE_PATH}")
        print()
        
        print("Connecting to server...")
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=USERNAME,
            password=PASSWORD,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        sftp = ssh_client.open_sftp()
        deployed_count = 0
        errors = []
        
        print("Deploying files...")
        print("-" * 80)
        
        for local_file, remote_file in FILES_TO_DEPLOY:
            try:
                if not os.path.exists(local_file):
                    print(f"[SKIP] {local_file} - File not found locally")
                    continue
                
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_file)
                stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()
                
                # Upload file
                sftp.put(local_file, remote_file)
                file_size = os.path.getsize(local_file)
                print(f"[OK] {local_file} -> {remote_file} ({file_size:,} bytes)")
                deployed_count += 1
                
            except Exception as e:
                error_msg = f"[ERROR] {local_file}: {str(e)}"
                print(error_msg)
                errors.append(error_msg)
        
        sftp.close()
        
        print()
        print("=" * 80)
        print(f"Deployment Summary: {deployed_count} files deployed")
        if errors:
            print(f"Errors: {len(errors)}")
            for error in errors:
                print(f"  {error}")
        print("=" * 80)
        
        # Restart services
        print()
        print("Restarting services to apply changes...")
        print("-" * 80)
        
        commands = [
            "systemctl restart python-proxy.service",
            "systemctl restart uwsgi",
            "systemctl reload nginx"
        ]
        
        for cmd in commands:
            try:
                stdin, stdout, stderr = ssh_client.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"[OK] {cmd}")
                else:
                    error_output = stderr.read().decode()
                    print(f"[WARN] {cmd} - Exit code: {exit_status}")
                    if error_output:
                        print(f"  Error: {error_output[:100]}")
            except Exception as e:
                print(f"[WARN] {cmd} - {str(e)}")
        
        ssh_client.close()
        
        print()
        print("=" * 80)
        print("[OK] DEPLOYMENT COMPLETE")
        print("=" * 80)
        print()
        print("Next steps:")
        print("1. Hard refresh your browser (Ctrl+Shift+R or Ctrl+F5)")
        print("2. Clear browser cache if changes don't appear")
        print("3. Check: https://masternoder.dk/vidgenerator/")
        print()
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)

