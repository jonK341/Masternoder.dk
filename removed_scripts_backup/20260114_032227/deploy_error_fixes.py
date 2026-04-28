"""
Deploy Error Fixes for Battle Intelligence System
"""
import paramiko
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

# Files to deploy
FILES_TO_DEPLOY = [
    'backend/services/activity_points_system.py',
    'backend/services/battle_intelligence_system.py',
    'backend/routes/activity_points_routes.py',
    'backend/routes/battle_intelligence_routes.py',
]

def deploy_files():
    """Deploy fixed files via SFTP"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sftp = None
    
    try:
        print("=" * 80)
        print("DEPLOYING ERROR FIXES FOR BATTLE INTELLIGENCE SYSTEM")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        sftp = ssh.open_sftp()
        
        base_path = Path.cwd()
        remote_base = "/var/www/html/vidgenerator"
        
        deployed_count = 0
        failed_count = 0
        
        for file_path in FILES_TO_DEPLOY:
            local_path = base_path / file_path
            remote_path = f"{remote_base}/{file_path}"
            
            if not local_path.exists():
                print(f"⚠️  File not found: {file_path}")
                failed_count += 1
                continue
            
            try:
                # Create remote directory if needed
                remote_dir = os.path.dirname(remote_path)
                stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
                stdout.read()
                
                # Upload file
                print(f"📤 Uploading: {file_path}")
                sftp.put(str(local_path), remote_path)
                
                # Set permissions
                ssh.exec_command(f"chmod 644 {remote_path}")
                ssh.exec_command(f"chown www-data:www-data {remote_path}")
                
                deployed_count += 1
                print(f"   ✅ Deployed to: {remote_path}")
                
            except Exception as e:
                print(f"   ❌ Failed: {e}")
                failed_count += 1
        
        print()
        print("=" * 80)
        print("DEPLOYMENT SUMMARY")
        print("=" * 80)
        print(f"✅ Successfully deployed: {deployed_count}")
        print(f"❌ Failed: {failed_count}")
        print()
        
        # Restart uWSGI service
        print("🔄 Restarting uWSGI service...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("✅ uWSGI service restarted successfully")
        else:
            error = stderr.read().decode()
            print(f"⚠️  uWSGI restart warning: {error}")
        
        # Wait a moment for service to start
        import time
        time.sleep(3)
        
        # Test endpoints
        print()
        print("🧪 Testing fixed endpoints...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/api/activity-points/leaderboard")
        status1 = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"Activity Points Leaderboard: {status1}")
        
        stdin, stdout, stderr = ssh.exec_command("curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:5000/api/battle/intelligence/mode/quick?user_id=test'")
        status2 = stdout.read().decode('utf-8', errors='ignore').strip()
        print(f"Battle Intelligence Quick: {status2}")
        
        if status1 == "200" and status2 == "200":
            print()
            print("✅ All endpoints working correctly!")
        else:
            print()
            print("⚠️  Some endpoints still returning errors. Check logs for details.")
        
        print()
        print("=" * 80)
        print("✅ DEPLOYMENT COMPLETE!")
        print("=" * 80)
        
        sftp.close()
        ssh.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Deployment error: {e}")
        import traceback
        traceback.print_exc()
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()
        return False

if __name__ == '__main__':
    success = deploy_files()
    sys.exit(0 if success else 1)

