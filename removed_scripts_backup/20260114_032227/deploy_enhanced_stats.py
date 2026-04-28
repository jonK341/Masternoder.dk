#!/usr/bin/env python3
"""
Deploy Enhanced Stats Tracking System
Deploys the enhanced stats tracking service and updated game routes
"""
import paramiko
import os
import sys
from pathlib import Path
from scp import SCPClient

# Server configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html/vidgenerator"
REMOTE_BACKEND = "/var/www/html"

# Files to deploy
FILES_TO_DEPLOY = [
    "backend/services/enhanced_stats_tracking.py",
    "backend/routes/game.py",
]

def deploy_files():
    """Deploy enhanced stats files to server"""
    try:
        print("=" * 70)
        print("DEPLOYING ENHANCED STATS TRACKING SYSTEM")
        print("=" * 70)
        print(f"Server: {SERVER_HOST}")
        print(f"Files to deploy: {len(FILES_TO_DEPLOY)}")
        print()
        
        # Verify files exist locally
        missing_files = []
        for file_path in FILES_TO_DEPLOY:
            if not os.path.exists(file_path):
                missing_files.append(file_path)
        
        if missing_files:
            print("[ERROR] Missing files:")
            for f in missing_files:
                print(f"  - {f}")
            return False
        
        print("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=60)
        print("[OK] Connected!")
        print()
        
        scp = SCPClient(ssh.get_transport())
        deployed_count = 0
        
        print("Deploying files...")
        print("-" * 70)
        
        for local_file in FILES_TO_DEPLOY:
            try:
                # Determine remote path (use forward slashes for Linux)
                if local_file.startswith('backend/services/'):
                    remote_file = f"{REMOTE_BACKEND}/{local_file}".replace("\\", "/")
                elif local_file.startswith('backend/routes/'):
                    remote_file = f"{REMOTE_BACKEND}/{local_file}".replace("\\", "/")
                else:
                    remote_file = f"{REMOTE_BASE}/{local_file}".replace("\\", "/")
                
                # Create remote directory if needed
                remote_dir = os.path.dirname(remote_file)
                stdin, stdout, stderr = ssh.exec_command(f'mkdir -p {remote_dir}')
                stdout.channel.recv_exit_status()
                
                # Deploy file
                print(f"[DEPLOY] {local_file} -> {remote_file}")
                scp.put(local_file, remote_file)
                deployed_count += 1
                print(f"[OK] Deployed successfully")
                
            except Exception as e:
                print(f"[ERROR] Failed to deploy {local_file}: {e}")
                continue
        
        scp.close()
        
        print()
        print("=" * 70)
        print(f"[OK] Deployment Complete!")
        print(f"    Deployed: {deployed_count}/{len(FILES_TO_DEPLOY)} files")
        print("=" * 70)
        print()
        
        # Restart services automatically
        print("Services need to be restarted for changes to take effect.")
        print("Restarting services now...")
        restart_services(ssh)
        
        ssh.close()
        return True
        
    except paramiko.AuthenticationException:
        print("[ERROR] Authentication failed. Check credentials.")
        return False
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH connection failed: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Deployment failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def restart_services(ssh_client):
    """Restart Python/Flask services"""
    try:
        print()
        print("-" * 70)
        print("Restarting services...")
        print("-" * 70)
        
        # Restart python-proxy service
        print("[INFO] Restarting python-proxy.service...")
        stdin, stdout, stderr = ssh_client.exec_command('sudo systemctl restart python-proxy.service')
        exit_status = stdout.channel.recv_exit_status()
        if exit_status == 0:
            print("[OK] python-proxy.service restarted")
        else:
            error_output = stderr.read().decode()
            print(f"[WARN] python-proxy.service restart may have failed: {error_output}")
        
        # Check if uwsgi is running
        print("[INFO] Checking for uwsgi service...")
        stdin, stdout, stderr = ssh_client.exec_command('systemctl list-units --type=service | grep -i uwsgi')
        uwsgi_check = stdout.read().decode()
        
        if 'uwsgi' in uwsgi_check.lower():
            print("[INFO] Restarting uwsgi service...")
            stdin, stdout, stderr = ssh_client.exec_command('sudo systemctl restart uwsgi')
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                print("[OK] uwsgi service restarted")
            else:
                print("[INFO] uwsgi service restart skipped (may not be active)")
        
        # Try to restart Flask app if running as a process
        print("[INFO] Checking for Flask processes...")
        stdin, stdout, stderr = ssh_client.exec_command('ps aux | grep -i "python.*run.py\\|flask\\|gunicorn" | grep -v grep')
        flask_processes = stdout.read().decode()
        
        if flask_processes:
            print("[INFO] Found Flask processes. Restarting may be needed.")
            print("[INFO] If using systemd services, they should restart automatically.")
        else:
            print("[INFO] No Flask processes found (may be running as service)")
        
        print()
        print("[OK] Service restart commands executed")
        print("[INFO] Wait a few seconds for services to fully restart")
        print()
        
    except Exception as e:
        print(f"[WARN] Error during service restart: {e}")
        print("[INFO] You may need to restart services manually")


def verify_deployment(ssh_client):
    """Verify files were deployed correctly"""
    try:
        print()
        print("-" * 70)
        print("Verifying deployment...")
        print("-" * 70)
        
        for local_file in FILES_TO_DEPLOY:
            if local_file.startswith('backend/services/'):
                remote_file = os.path.join(REMOTE_BACKEND, local_file)
            elif local_file.startswith('backend/routes/'):
                remote_file = os.path.join(REMOTE_BACKEND, local_file)
            else:
                remote_file = os.path.join(REMOTE_BASE, local_file)
            
            stdin, stdout, stderr = ssh_client.exec_command(f'test -f {remote_file} && echo "EXISTS" || echo "MISSING"')
            result = stdout.read().decode().strip()
            
            if result == "EXISTS":
                print(f"[OK] {remote_file} exists on server")
            else:
                print(f"[ERROR] {remote_file} NOT found on server")
        
    except Exception as e:
        print(f"[WARN] Verification error: {e}")


if __name__ == '__main__':
    print()
    print("Enhanced Stats Tracking System Deployment")
    print("=" * 70)
    print()
    
    # Check if running on Windows and warn about credentials
    if sys.platform == 'win32':
        if not SERVER_PASS or SERVER_PASS == "eD)2[K+[S#m_#$3!":
            print("[WARN] Using default password. Set DEPLOY_PASS environment variable for production.")
            print()
    
    success = deploy_files()
    
    if success:
        print()
        print("=" * 70)
        print("[SUCCESS] Enhanced Stats System Deployment Complete!")
        print("=" * 70)
        print()
        print("Next steps:")
        print("  1. Wait a few seconds for services to restart")
        print("  2. Test endpoints:")
        print("     - GET /vidgenerator/api/game/stats/comprehensive")
        print("     - GET /vidgenerator/api/game/stats/counts")
        print("  3. Check logs if there are any issues:")
        print("     - journalctl -u python-proxy.service -n 50")
        print()
        sys.exit(0)
    else:
        print()
        print("=" * 70)
        print("[ERROR] Deployment failed!")
        print("=" * 70)
        sys.exit(1)

