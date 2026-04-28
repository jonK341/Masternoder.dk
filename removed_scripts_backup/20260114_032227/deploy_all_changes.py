"""Deploy all recent changes: game, gallery, stats, index pages"""
import os
import sys
import paramiko
from pathlib import Path

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

# All files to deploy
FILES_TO_DEPLOY = [
    # Game files
    ("backend/routes/game.py", f"{REMOTE_PATH}/backend/routes/game.py"),
    ("vidgenerator/game/index.html", f"{REMOTE_PATH}/vidgenerator/game/index.html"),
    
    # Redesigned pages
    ("vidgenerator/index.html", f"{REMOTE_PATH}/vidgenerator/index.html"),
    ("vidgenerator/gallery/index.html", f"{REMOTE_PATH}/vidgenerator/gallery/index.html"),
    ("vidgenerator/stats/index.html", f"{REMOTE_PATH}/vidgenerator/stats/index.html"),
    ("vidgenerator/generator/index.html", f"{REMOTE_PATH}/vidgenerator/generator/index.html"),
    
    # Design system
    ("vidgenerator/static/css/modern-design-system.css", f"{REMOTE_PATH}/vidgenerator/static/css/modern-design-system.css"),
    
    # UI/UX improvements
    ("vidgenerator/static/css/loading-states.css", f"{REMOTE_PATH}/vidgenerator/static/css/loading-states.css"),
    ("vidgenerator/static/js/toast-notifications.js", f"{REMOTE_PATH}/vidgenerator/static/js/toast-notifications.js"),
    
    # Generator with quality fixes
    ("backend/routes/generator.py", f"{REMOTE_PATH}/backend/routes/generator.py"),
    
    # Gallery API fix
    ("backend/routes/gallery.py", f"{REMOTE_PATH}/backend/routes/gallery.py"),
    
    # Analytics dashboard
    ("backend/routes/analytics.py", f"{REMOTE_PATH}/backend/routes/analytics.py"),
    ("vidgenerator/analytics/index.html", f"{REMOTE_PATH}/vidgenerator/analytics/index.html"),
    ("backend/register_blueprints.py", f"{REMOTE_PATH}/backend/register_blueprints.py"),
    
    # Security enhancements
    ("src/utils/csrf_protection.py", f"{REMOTE_PATH}/src/utils/csrf_protection.py"),
    ("src/utils/security_logger.py", f"{REMOTE_PATH}/src/utils/security_logger.py"),
    ("src/utils/input_validator.py", f"{REMOTE_PATH}/src/utils/input_validator.py"),
    ("src/utils/rate_limiter.py", f"{REMOTE_PATH}/src/utils/rate_limiter.py"),
]

def deploy_all():
    """Deploy all files to server"""
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print("=" * 70)
        print("Deploying All Changes")
        print("=" * 70)
        print(f"Connecting to {SERVER_HOST}...")
        
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
        
        for local_file, remote_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"[SKIP] {local_file} - File not found")
                skipped_count += 1
                continue
            
            print(f"Uploading {local_file}...")
            
            # Ensure remote directory exists
            remote_dir = os.path.dirname(remote_file)
            stdin, stdout, stderr = ssh_client.exec_command(f"mkdir -p {remote_dir}")
            stdout.channel.recv_exit_status()
            
            # Upload file
            sftp.put(local_file, remote_file)
            print(f"[OK] Uploaded -> {remote_file}")
            deployed_count += 1
        
        sftp.close()
        
        print()
        print("=" * 70)
        print(f"[OK] Deployment Complete!")
        print(f"    Deployed: {deployed_count} files")
        print(f"    Skipped: {skipped_count} files")
        print("=" * 70)
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()
    
    return True

if __name__ == '__main__':
    success = deploy_all()
    sys.exit(0 if success else 1)

