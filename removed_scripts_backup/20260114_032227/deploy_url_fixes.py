"""
Deploy all URL fixes: navigation, buttons, static files, analytics
"""
import os
import sys
import paramiko
from pathlib import Path

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# All files modified for URL fixes
FILES_TO_DEPLOY = [
    # HTML Pages with navigation
    ("vidgenerator/game/index.html", f"{REMOTE_PATH}/vidgenerator/game/index.html"),
    ("vidgenerator/battle/index.html", f"{REMOTE_PATH}/vidgenerator/battle/index.html"),
    ("vidgenerator/social/index.html", f"{REMOTE_PATH}/vidgenerator/social/index.html"),
    ("vidgenerator/shop/index.html", f"{REMOTE_PATH}/vidgenerator/shop/index.html"),
    ("vidgenerator/stats/index.html", f"{REMOTE_PATH}/vidgenerator/stats/index.html"),
    ("vidgenerator/gallery/index.html", f"{REMOTE_PATH}/vidgenerator/gallery/index.html"),
    ("backend/templates/chat/index.html", f"{REMOTE_PATH}/backend/templates/chat/index.html"),
    
    # Python Backend
    ("backend/register_blueprints.py", f"{REMOTE_PATH}/backend/register_blueprints.py"),
    ("src/app.py", f"{REMOTE_PATH}/src/app.py"),
]

def restart_services(ssh_client):
    """Restart Flask/uWSGI and web server"""
    print("\n" + "=" * 70)
    print("Restarting Services")
    print("=" * 70)
    
    commands = [
        # Try to restart uWSGI service
        ("sudo systemctl restart uwsgi", "uWSGI service"),
        # Try to restart Flask service
        ("sudo systemctl restart flask-app", "Flask service"),
        # Try to restart via supervisor
        ("sudo supervisorctl restart flask-app", "Supervisor Flask"),
        # Reload Apache
        ("sudo service apache2 reload", "Apache"),
        # Reload Nginx (if Apache doesn't exist)
        ("sudo service nginx reload", "Nginx"),
    ]
    
    restarted = []
    for cmd, name in commands:
        try:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print(f"[OK] {name} restarted")
                restarted.append(name)
            else:
                error = stderr.read().decode()
                if "not found" not in error.lower() and "does not exist" not in error.lower():
                    print(f"[SKIP] {name} - exit code {exit_status}")
        except Exception as e:
            # Service might not exist, that's OK
            pass
    
    # Also try to find and restart Python processes
    try:
        print("\nChecking for Python/Flask processes...")
        stdin, stdout, stderr = ssh_client.exec_command("ps aux | grep -E '(flask|uwsgi|gunicorn|python.*run.py)' | grep -v grep", timeout=5)
        processes = stdout.read().decode().strip()
        if processes:
            print("[INFO] Found running processes:")
            for line in processes.split('\n'):
                if line.strip():
                    print(f"  {line[:80]}")
        else:
            print("[INFO] No Flask/uWSGI processes found (may be running as service)")
    except:
        pass
    
    if restarted:
        print(f"\n[OK] Restarted {len(restarted)} service(s): {', '.join(restarted)}")
    else:
        print("\n[WARN] Could not restart services automatically")
        print("       Please restart manually on server:")
        print("       sudo systemctl restart uwsgi")
        print("       sudo service apache2 reload")

def deploy_all():
    """Deploy all files to server and restart services"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Deploying URL Fixes")
        print("=" * 70)
        print(f"Server: {SERVER_HOST}")
        print(f"Remote Path: {REMOTE_PATH}")
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
        skipped_count = 0
        
        print("Uploading files...")
        print("-" * 70)
        
        for local_file, remote_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"[SKIP] {local_file} - File not found")
                skipped_count += 1
                continue
            
            try:
                # Ensure remote directory exists
                remote_dir = os.path.dirname(remote_file)
                stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
                stdout.channel.recv_exit_status()
                
                # Upload file
                sftp.put(local_file, remote_file)
                print(f"[OK] {local_file}")
                deployed_count += 1
                
            except Exception as e:
                print(f"[ERROR] {local_file} - {str(e)}")
                skipped_count += 1
        
        sftp.close()
        
        print()
        print("=" * 70)
        print(f"Deployment Complete!")
        print(f"  Deployed: {deployed_count} files")
        print(f"  Skipped: {skipped_count} files")
        print("=" * 70)
        
        # Restart services
        restart_services(ssh_client)
        
        print()
        print("=" * 70)
        print("[OK] Deployment and Service Restart Complete!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("1. Test pages: https://masternoder.dk/vidgenerator/game")
        print("2. Test static files: https://masternoder.dk/vidgenerator/static/css/modern-design-system.css")
        print("3. Test analytics: https://masternoder.dk/vidgenerator/analytics")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()

if __name__ == '__main__':
    success = deploy_all()
    sys.exit(0 if success else 1)

