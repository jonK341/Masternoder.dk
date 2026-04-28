#!/usr/bin/env python3
"""
Deploy Frontend Stats Integration
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
    print("DEPLOYING FRONTEND STATS INTEGRATION")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('vidgenerator/game/index.html', f'{REMOTE_PATH}/vidgenerator/game/index.html'),
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
    
    print("\n" + "=" * 80)
    print("✅ FRONTEND STATS INTEGRATION DEPLOYED!")
    print("=" * 80)
    print("\nFrontend Stats Integration:")
    print("  ✅ Advanced stats panel with tabs")
    print("  ✅ Trends tab - 7-day trend analysis")
    print("  ✅ Performance tab - Efficiency, activity, engagement metrics")
    print("  ✅ Time Series tab - XP progression over time")
    print("  ✅ Global tab - Platform-wide statistics")
    print("  ✅ Toggle button to show/hide advanced stats")
    print("  ✅ Tab switching functionality")
    print("  ✅ Real-time data loading from API endpoints")
    print("  ✅ Enhanced visualization with icons and formatting")
    print("  ✅ Error handling and loading states")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()

