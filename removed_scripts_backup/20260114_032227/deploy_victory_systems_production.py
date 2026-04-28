"""
Deploy Victory Systems to Production
Deploys all new victory systems, tech trees, and reconstructed unified points
"""
import os
import sys
import paramiko
import time
from pathlib import Path

# Server configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    # Victory System
    ("backend/services/victory_emblems_trophies.py", "backend/services/victory_emblems_trophies.py"),
    ("backend/routes/victory_tech_tree.py", "backend/routes/victory_tech_tree.py"),
    ("backend/routes/danish_divine_tech_tree.py", "backend/routes/danish_divine_tech_tree.py"),
    
    # Unified Points Reconstructed
    ("backend/services/unified_point_system_reconstructed.py", "backend/services/unified_point_system_reconstructed.py"),
    ("backend/routes/unified_points_reconstructed.py", "backend/routes/unified_points_reconstructed.py"),
    
    # Tech Tree Interfaces
    ("vidgenerator/victory-tech-tree/index.html", "vidgenerator/victory-tech-tree/index.html"),
    ("vidgenerator/danish-divine-tech-tree/index.html", "vidgenerator/danish-divine-tech-tree/index.html"),
    
    # Updated files
    ("backend/routes/ofc_api_routes.py", "backend/routes/ofc_api_routes.py"),
    ("backend/register_blueprints.py", "backend/register_blueprints.py"),
    ("backend/services/compass_hourglass_system.py", "backend/services/compass_hourglass_system.py"),
]

def deploy_file(ssh_client, local_path, remote_path):
    """Deploy a single file"""
    try:
        sftp = ssh_client.open_sftp()
        
        # Create remote directory if needed (use Unix path)
        remote_dir = remote_path.replace('\\', '/')
        remote_dir = os.path.dirname(remote_dir)
        ssh_client.exec_command(f"mkdir -p {remote_dir}")
        
        # Upload file (use Unix path for remote)
        remote_file = remote_path.replace('\\', '/')
        sftp.put(local_path, remote_file)
        sftp.close()
        
        return True
    except Exception as e:
        print(f"  ERROR: {str(e)}")
        return False

def deploy_all_files(ssh_client):
    """Deploy all files"""
    print("=" * 70)
    print("DEPLOYING FILES")
    print("=" * 70)
    print()
    
    success_count = 0
    fail_count = 0
    
    for local_path, remote_path in FILES_TO_DEPLOY:
        full_local = os.path.join(os.getcwd(), local_path)
        # Use Unix path for remote
        full_remote = f"{REMOTE_BASE}/{remote_path}".replace('\\', '/')
        
        if not os.path.exists(full_local):
            print(f"[SKIP] {local_path} (not found locally)")
            continue
        
        print(f"[DEPLOY] {local_path} -> {full_remote}")
        if deploy_file(ssh_client, full_local, full_remote):
            print(f"  OK Deployed")
            success_count += 1
        else:
            print(f"  FAILED")
            fail_count += 1
        print()
    
    print(f"Deployment Summary: {success_count} succeeded, {fail_count} failed")
    print()
    return success_count, fail_count

def clear_cache(ssh_client):
    """Clear Python cache"""
    print("=" * 70)
    print("CLEARING CACHE")
    print("=" * 70)
    print()
    
    commands = [
        f"find {REMOTE_BASE} -type d -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null || true",
        f"find {REMOTE_BASE} -type f -name '*.pyc' -delete 2>/dev/null || true",
        f"find {REMOTE_BASE} -type f -name '*.pyo' -delete 2>/dev/null || true",
    ]
    
    for cmd in commands:
        stdin, stdout, stderr = ssh_client.exec_command(cmd)
        stdout.channel.recv_exit_status()
    
    print("[OK] Cache cleared")
    print()

def restart_services(ssh_client):
    """Restart all production services"""
    print("=" * 70)
    print("RESTARTING SERVICES")
    print("=" * 70)
    print()
    
    # Stop old services
    print("[STOP] Stopping old services...")
    stop_commands = [
        "systemctl stop python-proxy.service 2>&1 || true",
        "systemctl stop vidgenerator.service 2>&1 || true",
        "pkill -f 'python.*run.py' 2>&1 || true",
        "pkill -f 'uwsgi.*vidgenerator' 2>&1 || true",
    ]
    
    for cmd in stop_commands:
        stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
        stdout.channel.recv_exit_status()
    
    time.sleep(2)
    print("[OK] Old services stopped")
    print()
    
    # Restart uWSGI (Flask app)
    print("[RESTART] uwsgi-vidgenerator.service...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi-vidgenerator.service 2>&1")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("[OK] uwsgi-vidgenerator.service restarted")
    else:
        error = stderr.read().decode()
        print(f"[WARN] {error.strip()}")
    time.sleep(2)
    print()
    
    # Restart python-proxy
    print("[RESTART] python-proxy.service...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart python-proxy.service 2>&1")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("[OK] python-proxy.service restarted")
    else:
        error = stderr.read().decode()
        print(f"[WARN] {error.strip()}")
    time.sleep(2)
    print()
    
    # Restart nginx
    print("[RESTART] nginx...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart nginx 2>&1")
    exit_status = stdout.channel.recv_exit_status()
    if exit_status == 0:
        print("[OK] nginx restarted")
    else:
        error = stderr.read().decode()
        print(f"[WARN] {error.strip()}")
    time.sleep(1)
    print()
    
    # Check service status
    print("[STATUS] Checking service status...")
    print("-" * 70)
    
    services_to_check = [
        ("uwsgi-vidgenerator.service", "uWSGI Flask App"),
        ("python-proxy.service", "Python Proxy"),
        ("nginx", "Nginx Web Server"),
    ]
    
    for service, name in services_to_check:
        stdin, stdout, stderr = ssh_client.exec_command(f"systemctl is-active {service} 2>&1")
        status = stdout.read().decode().strip()
        if status == "active":
            print(f"[OK] {name}: {status}")
        else:
            print(f"[WARN] {name}: {status}")
    print()

def verify_deployment(ssh_client):
    """Verify deployment"""
    print("=" * 70)
    print("VERIFYING DEPLOYMENT")
    print("=" * 70)
    print()
    
    # Check if files exist
    print("[CHECK] Checking deployed files...")
    for local_path, remote_path in FILES_TO_DEPLOY:
        full_remote = f"{REMOTE_BASE}/{remote_path}".replace('\\', '/')
        stdin, stdout, stderr = ssh_client.exec_command(f"test -f {full_remote} && echo 'EXISTS' || echo 'MISSING'")
        result = stdout.read().decode().strip()
        if result == "EXISTS":
            print(f"  OK {remote_path}")
        else:
            print(f"  MISSING {remote_path}")
    print()
    
    # Check data directory
    print("[CHECK] Checking data directory...")
    stdin, stdout, stderr = ssh_client.exec_command(f"test -d {REMOTE_BASE}/data && echo 'EXISTS' || echo 'MISSING'")
    result = stdout.read().decode().strip()
    if result == "EXISTS":
        print("  OK data/ directory exists")
    else:
        print("  WARN data/ directory missing (will be created on first use)")
    print()

def main():
    """Main deployment function"""
    print("=" * 70)
    print("VICTORY SYSTEMS PRODUCTION DEPLOYMENT")
    print("=" * 70)
    print(f"Server: {SERVER_HOST}")
    print(f"Remote Base: {REMOTE_BASE}")
    print()
    
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Connecting to {SERVER_HOST}...")
        ssh_client.connect(
            hostname=SERVER_HOST,
            username=SERVER_USER,
            password=SERVER_PASS,
            timeout=60
        )
        print("[OK] Connected!")
        print()
        
        # Step 1: Deploy files
        success, failed = deploy_all_files(ssh_client)
        
        # Step 2: Clear cache
        clear_cache(ssh_client)
        
        # Step 3: Restart services
        restart_services(ssh_client)
        
        # Step 4: Verify
        verify_deployment(ssh_client)
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 70)
        print(f"Files deployed: {success}")
        print(f"Files failed: {failed}")
        print()
        print("Services have been restarted.")
        print("New features should now be available at:")
        print("  - /vidgenerator/victory-tech-tree")
        print("  - /vidgenerator/danish-divine-tech-tree")
        print("  - /api/ofc/victory/* (API endpoints)")
        print("  - /api/points/* (Reconstructed unified points)")
        print()
        
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        ssh_client.close()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

