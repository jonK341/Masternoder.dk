#!/usr/bin/env python3
"""
Deploy Auto-Fix System
Deploys the auto-fix endpoint system to production
"""
import paramiko
import os
from scp import SCPClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html"

def deploy_auto_fix():
    """Deploy auto-fix system to server"""
    print("=" * 70)
    print("DEPLOYING AUTO-FIX SYSTEM")
    print("=" * 70)
    print()
    
    files_to_deploy = [
        ('backend/services/auto_fix_endpoints.py', f'{SERVER_BASE}/backend/services/auto_fix_endpoints.py'),
        ('backend/middleware/auto_fix_404_middleware.py', f'{SERVER_BASE}/backend/middleware/auto_fix_404_middleware.py'),
        ('backend/routes/auto_fix_routes.py', f'{SERVER_BASE}/backend/routes/auto_fix_routes.py'),
        ('backend/register_blueprints.py', f'{SERVER_BASE}/backend/register_blueprints.py'),
    ]
    
    # Try to find app/__init__.py in different locations
    app_init_paths = [
        'src/app/__init__.py',
        'app/__init__.py',
    ]
    
    for app_path in app_init_paths:
        local_path = os.path.join(BASE_DIR, app_path)
        if os.path.exists(local_path):
            files_to_deploy.append((app_path, f'{SERVER_BASE}/{app_path}'))
            break
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Create directories if needed
        print("[1/3] Creating directories...")
        commands = [
            f"mkdir -p {SERVER_BASE}/backend/middleware",
            f"mkdir -p {SERVER_BASE}/backend/services",
            f"mkdir -p {SERVER_BASE}/logs/auto_fix_endpoints",
            f"chmod 755 {SERVER_BASE}/backend/middleware",
            f"chmod 755 {SERVER_BASE}/backend/services",
            f"chmod 755 {SERVER_BASE}/logs/auto_fix_endpoints",
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            stdout.read()
        
        print("  [OK] Directories created")
        print()
        
        # Deploy files
        print("[2/3] Deploying files...")
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
        
        # Restart services
        print("[3/3] Restarting services...")
        restart_commands = [
            "systemctl restart uwsgi-vidgenerator",
            "systemctl restart python-proxy",
        ]
        
        for cmd in restart_commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
                result = stdout.read().decode('utf-8')
                if result:
                    print(f"  [OK] {cmd}")
                else:
                    print(f"  [OK] {cmd} (no output)")
            except Exception as e:
                print(f"  [WARN] {cmd}: {e}")
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Auto-fix system is now active!")
        print("It will automatically fix endpoints after 3+ 404 errors.")
        print()
        print("Test endpoints:")
        print("  - GET /vidgenerator/api/auto-fix/statistics")
        print("  - GET /vidgenerator/api/auto-fix/endpoints")
        print("  - GET /vidgenerator/api/auto-fix/patterns")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    deploy_auto_fix()
