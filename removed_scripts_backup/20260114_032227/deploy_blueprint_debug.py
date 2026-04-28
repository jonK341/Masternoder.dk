"""
Deploy blueprint registration debug
"""
import paramiko
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

FILES_TO_DEPLOY = [
    'backend/register_blueprints.py',
]

def deploy():
    """Deploy files"""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    sftp = None
    
    try:
        print("=" * 80)
        print("DEPLOYING BLUEPRINT DEBUG")
        print("=" * 80)
        print()
        
        ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
        sftp = ssh.open_sftp()
        
        base_path = Path.cwd()
        remote_base = "/var/www/html/vidgenerator"
        
        for file_path in FILES_TO_DEPLOY:
            local_path = base_path / file_path
            remote_path = f"{remote_base}/{file_path}"
            
            print(f"📤 Uploading: {file_path}")
            sftp.put(str(local_path), remote_path)
            ssh.exec_command(f"chmod 644 {remote_path}")
            ssh.exec_command(f"chown www-data:www-data {remote_path}")
            print(f"   ✅ Deployed")
        
        print()
        print("🔄 Restarting uWSGI service...")
        stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
        stdout.read()
        print("✅ Service restarted")
        
        print()
        print("📋 Checking startup logs...")
        print("-" * 80)
        stdin, stdout, stderr = ssh.exec_command("sleep 3 && journalctl -u uwsgi-vidgenerator.service -n 100 --no-pager | grep -i 'activity\|battle\|debug\|registered\|error' | tail -30")
        logs = stdout.read().decode('utf-8', errors='ignore')
        print(logs)
        
        sftp.close()
        ssh.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if sftp:
            sftp.close()
        if ssh:
            ssh.close()

if __name__ == '__main__':
    deploy()

