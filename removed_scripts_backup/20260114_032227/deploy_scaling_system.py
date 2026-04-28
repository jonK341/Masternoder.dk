#!/usr/bin/env python3
"""
Deploy Scaling System for 1.3 Billion Users
Deploys all scaling system files to the server
"""
import os
import sys
import subprocess
from pathlib import Path

# Configuration
BASE_DIR = Path(__file__).parent
REMOTE_HOST = "masternoder.dk"
REMOTE_USER = "root"
REMOTE_BASE = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    # Scaling services
    "backend/services/scaling_event_system.py",
    "backend/services/scaling_cache_system.py",
    "backend/services/scaling_queue_system.py",
    "backend/services/scaling_calculator_distributed.py",
    "backend/services/scaling_worker_service.py",
    "backend/services/scaling_startup.py",
    
    # Scaling routes
    "backend/routes/scaling_routes.py",
    
    # Blueprint registration
    "backend/register_blueprints.py",
]

def deploy_file(local_path, remote_path):
    """Deploy a single file using SCP"""
    local_full = BASE_DIR / local_path
    
    if not local_full.exists():
        print(f"[SKIP] {local_path} does not exist")
        return False
    
    try:
        # Create remote directory if needed
        remote_dir = os.path.dirname(remote_path)
        ssh_cmd = f"ssh {REMOTE_USER}@{REMOTE_HOST} 'mkdir -p {remote_dir}'"
        subprocess.run(ssh_cmd, shell=True, check=True, capture_output=True)
        
        # Copy file
        scp_cmd = f"scp {local_full} {REMOTE_USER}@{REMOTE_HOST}:{remote_path}"
        result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"[OK] Deployed {local_path} -> {remote_path}")
            return True
        else:
            print(f"[ERROR] Failed to deploy {local_path}: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Error deploying {local_path}: {e}")
        return False

def restart_services():
    """Restart Flask/uWSGI and Apache services"""
    try:
        # Restart uWSGI service
        print("\n[INFO] Restarting uWSGI service...")
        ssh_cmd = f"ssh {REMOTE_USER}@{REMOTE_HOST} 'systemctl restart uwsgi-vidgenerator.service'"
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[OK] uWSGI service restarted")
        else:
            print(f"[WARN] uWSGI restart warning: {result.stderr}")
        
        # Check uWSGI status
        status_cmd = f"ssh {REMOTE_USER}@{REMOTE_HOST} 'systemctl status uwsgi-vidgenerator.service --no-pager -l | head -20'"
        subprocess.run(status_cmd, shell=True)
        
        # Restart Apache
        print("\n[INFO] Restarting Apache service...")
        apache_cmd = f"ssh {REMOTE_USER}@{REMOTE_HOST} 'systemctl restart apache2.service'"
        result = subprocess.run(apache_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("[OK] Apache service restarted")
        else:
            print(f"[WARN] Apache restart warning: {result.stderr}")
        
        # Check Apache status
        apache_status_cmd = f"ssh {REMOTE_USER}@{REMOTE_HOST} 'systemctl status apache2.service --no-pager -l | head -20'"
        subprocess.run(apache_status_cmd, shell=True)
        
        return True
    except Exception as e:
        print(f"[ERROR] Error restarting services: {e}")
        return False

def main():
    """Main deployment function"""
    print("=" * 60)
    print("Deploying Scaling System for 1.3 Billion Users")
    print("=" * 60)
    print()
    
    deployed_count = 0
    failed_count = 0
    
    for local_file in FILES_TO_DEPLOY:
        remote_file = os.path.join(REMOTE_BASE, local_file)
        if deploy_file(local_file, remote_file):
            deployed_count += 1
        else:
            failed_count += 1
    
    print()
    print("=" * 60)
    print(f"Deployment Summary: {deployed_count} succeeded, {failed_count} failed")
    print("=" * 60)
    
    if failed_count == 0:
        print("\n[INFO] All files deployed successfully. Restarting services...")
        restart_services()
        print("\n[OK] Deployment complete!")
        return 0
    else:
        print(f"\n[WARN] {failed_count} files failed to deploy")
        return 1

if __name__ == "__main__":
    sys.exit(main())

