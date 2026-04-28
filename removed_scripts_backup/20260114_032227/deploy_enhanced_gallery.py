#!/usr/bin/env python3
"""
Deploy Enhanced Gallery Features
"""
import os
import sys
import paramiko
from scp import SCPClient

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_PATH = "/var/www/html/vidgenerator"

ssh_client = paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
scp = None

try:
    print("=" * 80)
    print("DEPLOYING ENHANCED GALLERY FEATURES")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('vidgenerator/gallery/index.html', f'{REMOTE_PATH}/vidgenerator/gallery/index.html'),
        ('backend/routes/gallery.py', f'{REMOTE_PATH}/backend/routes/gallery.py'),
    ]
    
    for local_path, remote_path in files_to_deploy:
        print(f"\n1. Deploying {local_path}...")
        scp.put(local_path, remote_path)
        print(f"   [OK] Deployed to {remote_path}")
    
    print("\n2. Setting file permissions...")
    for _, remote_path in files_to_deploy:
        stdin, stdout, stderr = ssh_client.exec_command(f"chmod 644 {remote_path} && chown www-data:www-data {remote_path} 2>&1")
        output = stdout.read().decode('utf-8', errors='ignore')
        if output.strip():
            print(f"   {output}")
    
    print("\n3. Restarting uWSGI service...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi 2>&1")
    restart_output = stdout.read().decode('utf-8', errors='ignore')
    if restart_output.strip():
        print(f"   {restart_output}")
    else:
        print("   [OK] Service restarted")
    
    print("\n" + "=" * 80)
    print("✅ ENHANCED GALLERY DEPLOYED!")
    print("=" * 80)
    print("\nGallery Enhancements:")
    print("  ✅ Category filter dropdown")
    print("  ✅ Quality level filter")
    print("  ✅ Advanced filters panel with:")
    print("     - Date range filtering")
    print("     - Quality score range")
    print("     - Duration range")
    print("  ✅ View options (Grid/List view)")
    print("  ✅ Results count display")
    print("  ✅ Enhanced sorting (by quality score)")
    print("  ✅ Client-side advanced filtering")
    print("  ✅ Better metadata display")
    print("  ✅ URL parameter persistence")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()

