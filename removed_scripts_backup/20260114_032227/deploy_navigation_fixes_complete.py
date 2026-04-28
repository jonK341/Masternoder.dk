"""
Deploy Complete Navigation Fixes
Deploys all navigation fixes, missing routes, and ensures all links work
"""
import os
import sys
import paramiko
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html/vidgenerator"

FILES_TO_DEPLOY = [
    # Navigation files
    ("vidgenerator/static/js/navigation-toolbar.js", "vidgenerator/static/js/navigation-toolbar.js"),
    ("vidgenerator/static/js/navigation.js", "vidgenerator/static/js/navigation.js"),
    
    # Missing route handlers
    ("backend/routes/missing_page_routes.py", "backend/routes/missing_page_routes.py"),
    
    # Updated blueprint registration
    ("backend/register_blueprints.py", "backend/register_blueprints.py"),
]

def deploy_file(ssh_client, local_path, remote_path):
    """Deploy a single file"""
    try:
        sftp = ssh_client.open_sftp()
        remote_dir = remote_path.replace('\\', '/')
        remote_dir = os.path.dirname(remote_dir)
        ssh_client.exec_command(f"mkdir -p {remote_dir}")
        remote_file = remote_path.replace('\\', '/')
        sftp.put(local_path, remote_file)
        sftp.close()
        return True
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def main():
    print("=" * 70)
    print("DEPLOYING COMPLETE NAVIGATION FIXES")
    print("=" * 70)
    
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {SERVER_HOST}...")
        ssh_client.connect(hostname=SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected!")
        print()
        
        # Deploy files
        success_count = 0
        for local_path, remote_path in FILES_TO_DEPLOY:
            full_local = os.path.join(os.getcwd(), local_path)
            full_remote = f"{REMOTE_BASE}/{remote_path}".replace('\\', '/')
            
            if not os.path.exists(full_local):
                print(f"[SKIP] {local_path} (not found)")
                continue
            
            print(f"[DEPLOY] {local_path}")
            if deploy_file(ssh_client, full_local, full_remote):
                print(f"  [OK]")
                success_count += 1
            else:
                print(f"  [FAILED]")
            print()
        
        # Clear cache
        print("[CLEAR] Cache...")
        ssh_client.exec_command(f"find {REMOTE_BASE} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null || true")
        ssh_client.exec_command(f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true")
        print("[OK] Cache cleared")
        print()
        
        # Restart services
        print("[RESTART] Services...")
        ssh_client.exec_command("systemctl restart uwsgi-vidgenerator.service 2>&1")
        time.sleep(2)
        ssh_client.exec_command("systemctl restart python-proxy.service 2>&1")
        time.sleep(2)
        print("[OK] Services restarted")
        print()
        
        print(f"Deployment complete: {success_count}/{len(FILES_TO_DEPLOY)} files")
        
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
    finally:
        ssh_client.close()

if __name__ == "__main__":
    main()

