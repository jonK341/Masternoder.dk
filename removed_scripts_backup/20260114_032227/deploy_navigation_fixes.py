"""
Deploy Navigation Fixes to Production
Deploys all navigation updates, link fixes, and tech tree pages
"""
import os
import sys
import paramiko
import time

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    # Navigation JavaScript files
    ("vidgenerator/static/js/navigation-toolbar.js", "vidgenerator/static/js/navigation-toolbar.js"),
    ("vidgenerator/static/js/navigation.js", "vidgenerator/static/js/navigation.js"),
    
    # Tech Tree HTML files (with fixed links)
    ("vidgenerator/victory-tech-tree/index.html", "vidgenerator/victory-tech-tree/index.html"),
    ("vidgenerator/danish-divine-tech-tree/index.html", "vidgenerator/danish-divine-tech-tree/index.html"),
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
    print("DEPLOYING NAVIGATION FIXES")
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
        
        # Deploy files
        print("=" * 70)
        print("DEPLOYING FILES")
        print("=" * 70)
        print()
        
        success_count = 0
        fail_count = 0
        
        for local_path, remote_path in FILES_TO_DEPLOY:
            full_local = os.path.join(os.getcwd(), local_path)
            full_remote = f"{REMOTE_BASE}/{remote_path}".replace('\\', '/')
            
            if not os.path.exists(full_local):
                print(f"[SKIP] {local_path} (not found locally)")
                continue
            
            print(f"[DEPLOY] {local_path}")
            print(f"  -> {full_remote}")
            if deploy_file(ssh_client, full_local, full_remote):
                print(f"  [OK] Deployed")
                success_count += 1
            else:
                print(f"  [FAILED]")
                fail_count += 1
            print()
        
        print(f"Deployment Summary: {success_count} succeeded, {fail_count} failed")
        print()
        
        # Clear cache
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
        
        # Restart services
        print("=" * 70)
        print("RESTARTING SERVICES")
        print("=" * 70)
        print()
        
        # Stop old services
        print("[STOP] Stopping old services...")
        stop_commands = [
            "systemctl stop python-proxy.service 2>&1 || true",
            "pkill -f 'python.*run.py' 2>&1 || true",
            "pkill -f 'uwsgi.*vidgenerator' 2>&1 || true",
        ]
        
        for cmd in stop_commands:
            stdin, stdout, stderr = ssh_client.exec_command(cmd, timeout=10)
            stdout.channel.recv_exit_status()
        
        time.sleep(2)
        print("[OK] Old services stopped")
        print()
        
        # Restart uWSGI
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
        print("=" * 70)
        print("SERVICE STATUS")
        print("=" * 70)
        print()
        
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
        
        # Verify deployment
        print("=" * 70)
        print("VERIFYING DEPLOYMENT")
        print("=" * 70)
        print()
        
        for local_path, remote_path in FILES_TO_DEPLOY:
            full_remote = f"{REMOTE_BASE}/{remote_path}".replace('\\', '/')
            stdin, stdout, stderr = ssh_client.exec_command(f"test -f {full_remote} && echo 'EXISTS' || echo 'MISSING'")
            result = stdout.read().decode().strip()
            if result == "EXISTS":
                print(f"  [OK] {remote_path}")
            else:
                print(f"  [MISSING] {remote_path}")
        print()
        
        print("=" * 70)
        print("DEPLOYMENT COMPLETE!")
        print("=" * 70)
        print(f"Files deployed: {success_count}")
        print(f"Files failed: {fail_count}")
        print()
        print("Navigation fixes are now live!")
        print("Updated features:")
        print("  - Navigation toolbar with tech tree links")
        print("  - Standard navigation with tech tree links")
        print("  - Fixed links in tech tree pages")
        print("  - All URLs use /vidgenerator prefix")
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

