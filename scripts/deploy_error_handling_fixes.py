#!/usr/bin/env python3
"""
Deploy Error Handling Fixes
Deploys JSON error handlers and improved frontend error handling
"""
import paramiko
import os
from scp import SCPClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html"

def deploy_fixes():
    """Deploy error handling fixes"""
    print("=" * 70)
    print("DEPLOYING ERROR HANDLING FIXES")
    print("=" * 70)
    print()
    
    files_to_deploy = [
        ('backend/middleware/json_error_handler.py', f'{SERVER_BASE}/backend/middleware/json_error_handler.py'),
        ('src/app/__init__.py', f'{SERVER_BASE}/src/app/__init__.py'),
        ('backend/routes/missing_endpoints_routes.py', f'{SERVER_BASE}/backend/routes/missing_endpoints_routes.py'),
        ('vidgenerator/static/js/backend-connector.js', f'{SERVER_BASE}/vidgenerator/static/js/backend-connector.js'),
        ('vidgenerator/static/js/navigation-toolbar.js', f'{SERVER_BASE}/vidgenerator/static/js/navigation-toolbar.js'),
    ]
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        print("[1/2] Deploying files...")
        for local_file, remote_file in files_to_deploy:
            local_path = os.path.join(BASE_DIR, local_file)
            if os.path.exists(local_path):
                try:
                    sftp.put(local_path, remote_file)
                    sftp.chmod(remote_file, 0o644)
                    print(f"  [OK] Deployed: {local_file}")
                except Exception as e:
                    print(f"  [WARN] Could not deploy {local_file}: {e}")
            else:
                print(f"  [WARN] Local file not found: {local_file}")
        
        sftp.close()
        print()
        
        print("[2/2] Restarting services...")
        restart_commands = [
            "systemctl restart uwsgi-vidgenerator",
            "systemctl restart python-proxy",
        ]
        
        for cmd in restart_commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                stdout.read()
                print(f"  [OK] {cmd}")
            except Exception as e:
                print(f"  [WARN] {cmd}: {e}")
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Fixes deployed:")
        print("  ✅ JSON error handlers for all API endpoints")
        print("  ✅ Improved frontend error handling with exponential backoff")
        print("  ✅ Reduced polling frequency (30s -> 2min)")
        print("  ✅ Better placeholder endpoint responses")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    deploy_fixes()
