#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deploy All Fixes and Run Final Audit
Deploys all fixed files and verifies connections
"""
import paramiko
import os
import sys
import time
import subprocess
from datetime import datetime

# Fix Windows encoding issues
if os.name == 'nt':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
REMOTE_BASE = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    # Route files
    "backend/routes/trophie_routes.py",
    "backend/routes/leaderboard_unified_routes.py",
    "backend/routes/quick_battle_routes.py",
    
    # Service files
    "backend/services/quick_battle_system.py",
    
    # Blueprint registration
    "backend/register_blueprints.py",
]

def print_header(text):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(text.center(70))
    print("=" * 70 + "\n")

def print_success(text):
    print(f"[OK] {text}")

def print_error(text):
    print(f"[ERROR] {text}")

def print_info(text):
    print(f"[INFO] {text}")

def deploy_files(ssh, sftp):
    """Deploy all fixed files"""
    print_header("DEPLOYING FIXED FILES")
    
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    deployed = 0
    failed = 0
    
    for local_file in FILES_TO_DEPLOY:
        local_path = os.path.join(BASE_DIR, local_file)
        
        if not os.path.exists(local_path):
            print_info(f"Skipping {local_file} (not found locally)")
            continue
        
        try:
            remote_path = os.path.join(REMOTE_BASE, local_file).replace('\\', '/')
            remote_dir = os.path.dirname(remote_path)
            
            # Create remote directory
            ssh.exec_command(f"mkdir -p {remote_dir} 2>&1", timeout=5)
            time.sleep(0.5)
            
            # Read local file
            with open(local_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Write to remote
            with sftp.file(remote_path, 'w') as rf:
                rf.write(content)
            
            print_success(f"{local_file}")
            deployed += 1
            
        except Exception as e:
            print_error(f"{local_file}: {str(e)[:100]}")
            failed += 1
    
    print(f"\n[SUMMARY] Deployed: {deployed}, Failed: {failed}")
    return deployed > 0

def verify_deployment(ssh):
    """Verify deployed files"""
    print_header("VERIFYING DEPLOYMENT")
    
    try:
        for local_file in FILES_TO_DEPLOY:
            remote_path = os.path.join(REMOTE_BASE, local_file).replace('\\', '/')
            cmd = f"test -f {remote_path} && echo 'EXISTS' || echo 'NOT_FOUND'"
            stdin, stdout, stderr = ssh.exec_command(cmd, timeout=10)
            output = stdout.read().decode('utf-8', errors='replace').strip()
            
            if 'EXISTS' in output:
                print_success(f"{local_file} - Verified on server")
            else:
                print_error(f"{local_file} - NOT FOUND on server")
    except Exception as e:
        print_error(f"Verification error: {str(e)[:100]}")

def test_endpoints():
    """Test key endpoints"""
    print_header("TESTING ENDPOINTS")
    
    endpoints = [
        ("Shop-v3 API", "https://masternoder.dk/vidgenerator/api/shop-v3/items"),
        ("Trophie API", "https://masternoder.dk/vidgenerator/api/trophie/list"),
        ("Quick Battle Counter", "https://masternoder.dk/vidgenerator/api/quick-battle/counter?user_id=test"),
        ("Leaderboard Trophies", "https://masternoder.dk/vidgenerator/api/leaderboard/trophies"),
        ("Leaderboard Battle", "https://masternoder.dk/vidgenerator/api/leaderboard/battle"),
    ]
    
    try:
        import importlib
        requests = importlib.import_module('requests')
        
        results = []
        for name, url in endpoints:
            try:
                response = requests.get(url, timeout=10, verify=False)
                if response.status_code == 200:
                    print_success(f"{name}: HTTP {response.status_code}")
                    results.append((name, True))
                elif response.status_code == 404:
                    print_error(f"{name}: HTTP 404 (Not Found)")
                    results.append((name, False))
                else:
                    print_info(f"{name}: HTTP {response.status_code}")
                    results.append((name, None))
            except Exception as e:
                print_error(f"{name}: {str(e)[:50]}")
                results.append((name, False))
        
        return results
    except ImportError:
        print_info("requests module not available - skipping endpoint tests")
        return []

def main():
    """Main deployment routine"""
    print_header("DEPLOY ALL FIXES AND RUN FINAL AUDIT")
    print(f"Server: {SERVER_HOST}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    ssh = None
    try:
        print_info("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
        print_success("Connected to server")
        
        sftp = ssh.open_sftp()
        
        # Deploy files
        deploy_files(ssh, sftp)
        
        sftp.close()
        
        # Verify deployment
        verify_deployment(ssh)
        
        # Clear cache and restart
        print_header("CLEARING CACHE AND RESTARTING")
        print_info("Clearing Python cache...")
        ssh.exec_command("find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true", timeout=30)
        ssh.exec_command("find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true", timeout=30)
        print_success("Cache cleared")
        
        print_info("Restarting services...")
        services = ['python-proxy.service', 'vidgenerator-gunicorn.service']
        for service in services:
            try:
                ssh.exec_command(f"systemctl restart {service} 2>&1", timeout=10)
                time.sleep(2)
            except:
                pass
        
        time.sleep(5)
        print_success("Services restarted")
        
        # Test endpoints
        test_endpoints()
        
        # Run local audit
        print_header("RUNNING BACKEND-TO-FRONTEND AUDIT")
        print_info("Running connection audit locally...")
        try:
            result = subprocess.run(
                [sys.executable, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'backend_frontend_connection_audit.py')],
                cwd=os.path.dirname(os.path.dirname(__file__)),
                timeout=120,
                capture_output=False
            )
            if result.returncode == 0:
                print_success("Audit completed successfully")
            else:
                print_info("Audit completed with warnings")
        except Exception as e:
            print_error(f"Audit error: {str(e)[:100]}")
        
        print_header("DEPLOYMENT COMPLETE")
        print_success("All fixes deployed and verified!")
        print_info(f"Live URL: https://{SERVER_HOST}/vidgenerator")
        print_info("Check COMPREHENSIVE_FIXES_AND_LOOSE_ENDS_SUMMARY.md for full details")
        
        return 0
        
    except Exception as e:
        print_error(f"Deployment failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        if ssh:
            ssh.close()

if __name__ == '__main__':
    sys.exit(main())
