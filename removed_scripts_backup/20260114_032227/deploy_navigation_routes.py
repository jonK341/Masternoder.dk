"""
Deploy Navigation Route Fixes to Production
Fixes all missing page routes for navigation links
"""
import paramiko
import os
import sys

# Configure stdout for Unicode
sys.stdout.reconfigure(encoding='utf-8')

# Server configuration
SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
SERVER_USER = os.getenv("DEPLOY_USER", "root")
SERVER_PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
SERVER_PORT = 22

# Paths
LOCAL_BASE = os.getcwd()
REMOTE_BASE = "/var/www/html/vidgenerator"

# Files to deploy
FILES_TO_DEPLOY = [
    {
        "local": "backend/routes/all_page_routes.py",
        "remote": "backend/routes/all_page_routes.py"
    },
    {
        "local": "backend/register_blueprints.py",
        "remote": "backend/register_blueprints.py"
    }
]

def deploy_file(ssh, sftp, local_path, remote_path):
    """Deploy a single file"""
    try:
        # Use absolute path for local file
        local_full = os.path.abspath(os.path.join(LOCAL_BASE, local_path))
        
        # Check if local file exists
        if not os.path.exists(local_full):
            print(f"⚠️  Warning: Local file not found: {local_full}")
            return False
        
        # Construct remote path (use forward slashes for remote)
        remote_full = f"{REMOTE_BASE}/{remote_path}".replace('\\', '/')
        
        # Create remote directory if needed
        remote_dir = os.path.dirname(remote_full).replace('\\', '/')
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.channel.recv_exit_status()
        
        # Deploy file using absolute local path
        sftp.put(local_full, remote_full)
        
        # Set permissions
        ssh.exec_command(f"chmod 644 {remote_full}")
        
        print(f"✅ Deployed: {local_path} -> {remote_full}")
        return True
    except Exception as e:
        print(f"❌ Error deploying {local_path}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("=" * 70)
    print("DEPLOYING NAVIGATION ROUTE FIXES")
    print("=" * 70)
    print(f"Server: {SERVER_USER}@{SERVER_HOST}:{SERVER_PORT}")
    print(f"Remote Base: {REMOTE_BASE}")
    print()
    
    try:
        # Connect to server
        print("Connecting to server...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(
            SERVER_HOST, 
            port=SERVER_PORT, 
            username=SERVER_USER,
            password=SERVER_PASSWORD,
            timeout=60
        )
        sftp = ssh.open_sftp()
        print("✅ Connected")
        print()
        
        # Deploy files
        print("Deploying files...")
        deployed = 0
        for file_info in FILES_TO_DEPLOY:
            if deploy_file(ssh, sftp, file_info["local"], file_info["remote"]):
                deployed += 1
        print()
        
        if deployed == 0:
            print("❌ No files deployed. Exiting.")
            sftp.close()
            ssh.close()
            sys.exit(1)
        
        # Clear Python cache
        print("Clearing Python cache...")
        commands = [
            f"find {REMOTE_BASE}/backend -type d -name '__pycache__' -exec rm -r {{}} + 2>/dev/null || true",
            f"find {REMOTE_BASE}/backend -type f -name '*.pyc' -delete 2>/dev/null || true",
        ]
        
        for cmd in commands:
            stdin, stdout, stderr = ssh.exec_command(cmd)
            stdout.channel.recv_exit_status()
        print("✅ Cache cleared")
        print()
        
        # Restart services
        print("Restarting services...")
        restart_commands = [
            "systemctl restart uwsgi",
            "systemctl restart python-proxy",
        ]
        
        restart_success = 0
        for cmd in restart_commands:
            try:
                stdin, stdout, stderr = ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                if exit_status == 0:
                    print(f"✅ {cmd}")
                    restart_success += 1
                else:
                    error = stderr.read().decode()
                    print(f"⚠️  {cmd} (exit code: {exit_status})")
                    if error:
                        print(f"   Error: {error[:100]}")
            except Exception as e:
                print(f"⚠️  {cmd} failed: {e}")
        print()
        
        # Close connections
        sftp.close()
        ssh.close()
        
        # Summary
        print("=" * 70)
        print("DEPLOYMENT COMPLETE")
        print("=" * 70)
        print(f"Files Deployed: {deployed}/{len(FILES_TO_DEPLOY)}")
        print(f"Services Restarted: {restart_success}/{len(restart_commands)}")
        print("Cache Cleared: Yes")
        print()
        print("Updated Features:")
        print("  - All page routes handler (dashboard, battle, stats, etc.)")
        print("  - Unified route handler for all navigation links")
        print("  - Blueprint registration updated")
        print()
        print("✅ All navigation links should now work!")
        print()
        print("Next step: Run 'python test_navigation_links.py' to verify")
        
    except paramiko.AuthenticationException:
        print("❌ Authentication failed. Check credentials.")
        print("   Set DEPLOY_PASS environment variable or update script")
        sys.exit(1)
    except paramiko.SSHException as e:
        print(f"❌ SSH connection error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

