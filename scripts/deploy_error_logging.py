#!/usr/bin/env python3
"""
Deploy Error Logging System
Deploys the error logging system to production
"""
import paramiko
import os
from scp import SCPClient

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

SERVER_BASE = "/var/www/html"

def deploy_error_logging():
    """Deploy error logging system"""
    print("=" * 70)
    print("DEPLOYING ERROR LOGGING SYSTEM")
    print("=" * 70)
    print()
    
    files_to_deploy = [
        ('backend/services/error_logging.py', f'{SERVER_BASE}/backend/services/error_logging.py'),
        ('backend/middleware/error_logging_middleware.py', f'{SERVER_BASE}/backend/middleware/error_logging_middleware.py'),
        ('backend/routes/error_logging_routes.py', f'{SERVER_BASE}/backend/routes/error_logging_routes.py'),
        ('src/app/__init__.py', f'{SERVER_BASE}/src/app/__init__.py'),
        ('backend/register_blueprints.py', f'{SERVER_BASE}/backend/register_blueprints.py'),
    ]
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        sftp = ssh.open_sftp()
        
        # Create directories
        print("[1/3] Creating directories...")
        commands = [
            f"mkdir -p {SERVER_BASE}/logs/errors",
            f"chmod 755 {SERVER_BASE}/logs/errors",
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
                stdout.read()
                print(f"  [OK] {cmd}")
            except Exception as e:
                print(f"  [WARN] {cmd}: {e}")
        
        print()
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print()
        print("Error logging system is now active!")
        print()
        print("API Endpoints:")
        print("  - GET /vidgenerator/api/errors/statistics")
        print("  - GET /vidgenerator/api/errors/recent")
        print("  - GET /vidgenerator/api/errors/by-type/<error_type>")
        print("  - GET /vidgenerator/api/errors/by-endpoint")
        
        ssh.close()
        
    except Exception as e:
        print(f"  [ERROR] {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    deploy_error_logging()
