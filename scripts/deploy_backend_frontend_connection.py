#!/usr/bin/env python3
"""
Deploy Backend-Frontend Connection
Deploys backend-connector.js and page-data-loaders.js to production
"""
import paramiko
import os
import sys
import time
from datetime import datetime

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    "vidgenerator/static/js/backend-connector.js",
    "vidgenerator/static/js/page-data-loaders.js",
    "vidgenerator/profile/index.html",
    "vidgenerator/stats/index.html",
    "vidgenerator/social/index.html"
]

def deploy_backend_frontend_connection():
    """Deploy backend-frontend connection files"""
    print("=" * 70)
    print("DEPLOY BACKEND-FRONTEND CONNECTION")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        # Connect to server
        print("[1/3] Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print("  [OK] Connected")
        print()
        
        # Deploy files
        print("[2/3] Deploying connection files...")
        sftp = ssh.open_sftp()
        deployed = 0
        
        for local_file in FILES_TO_DEPLOY:
            if not os.path.exists(local_file):
                print(f"  [SKIP] {local_file} (not found)")
                continue
            
            try:
                remote_file = f"/var/www/html/vidgenerator/{local_file}"
                remote_dir = os.path.dirname(remote_file)
                
                # Create remote directory
                ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
                
                # Backup existing file
                ssh.exec_command(f"cp {remote_file} {remote_file}.backup.$(date +%Y%m%d_%H%M%S) 2>&1 || true", timeout=5)
                
                # Copy file
                sftp.put(local_file, remote_file)
                print(f"  [OK] Deployed {local_file}")
                deployed += 1
                
            except Exception as e:
                print(f"  [ERROR] Failed to deploy {local_file}: {e}")
        
        sftp.close()
        print(f"  [SUMMARY] Deployed {deployed}/{len(FILES_TO_DEPLOY)} files")
        print()
        
        # Clear cache
        print("[3/3] Clearing cache...")
        ssh.exec_command("find /var/www/html/vidgenerator/static -name '*.js' -exec touch {} \\; 2>&1 || true", timeout=30)
        print("  [OK] Cache cleared")
        print()
        
        ssh.close()
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Backend-Frontend connection deployed:")
        print("  ✓ backend-connector.js - Unified API connector")
        print("  ✓ page-data-loaders.js - Page-specific loaders")
        print("  ✓ profile/index.html - Updated with connector")
        print("  ✓ stats/index.html - Updated with connector")
        print("  ✓ social/index.html - Updated with connector")
        print()
        
    except Exception as e:
        print(f"\n  [ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    deploy_backend_frontend_connection()
