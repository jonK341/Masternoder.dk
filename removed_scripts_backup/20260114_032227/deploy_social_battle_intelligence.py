#!/usr/bin/env python3
"""
Deploy Social and Battle pages with intelligence and resources
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
    print("DEPLOYING SOCIAL & BATTLE PAGES WITH INTELLIGENCE & RESOURCES")
    print("=" * 80)
    
    ssh_client.connect(hostname=SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    scp = SCPClient(ssh_client.get_transport())
    
    files_to_deploy = [
        ('vidgenerator/social/index.html', f'{REMOTE_PATH}/vidgenerator/social/index.html'),
        ('vidgenerator/battle/index.html', f'{REMOTE_PATH}/vidgenerator/battle/index.html'),
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
    
    print("\n3. Restarting services...")
    stdin, stdout, stderr = ssh_client.exec_command("systemctl restart uwsgi-vidgenerator.service 2>&1")
    output = stdout.read().decode('utf-8', errors='ignore')
    if output.strip():
        print(f"   {output}")
    else:
        print("   [OK] uWSGI restarted")
    
    print("\n" + "=" * 80)
    print("✅ DEPLOYMENT COMPLETE!")
    print("=" * 80)
    print("\nNew Features Added:")
    print("  🧠 Intelligence Systems:")
    print("     - Player Profiler with triggers and analytics")
    print("     - Media Gatherer intelligence")
    print("     - Battle-specific intelligence")
    print("     - Strategic intelligence (clans, competitors)")
    print("  💎 Resources:")
    print("     - Inventory & Items management")
    print("     - Artifacts collection with stories")
    print("     - XP & Stats resources")
    print("     - Resource statistics and impact")
    print("\nPages Updated:")
    print("  - /vidgenerator/social (with Intelligence & Resources tabs)")
    print("  - /vidgenerator/battle (with Intelligence & Resources tabs)")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
finally:
    if scp:
        scp.close()
    ssh_client.close()

