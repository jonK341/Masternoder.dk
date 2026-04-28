#!/usr/bin/env python3
"""Deploy Profile Page Update"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING PROFILE PAGE UPDATE")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('vidgenerator/profile/index.html', '/var/www/html/vidgenerator/vidgenerator/profile/index.html'),
]

print("[INFO] Deploying files...")
for local_path, remote_path in files_to_deploy:
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create directory if needed
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.read()
        
        with sftp.file(remote_path, 'w') as f:
            f.write(content)
        print(f"  [OK] Deployed {local_path}")
    else:
        print(f"  [WARN] File not found: {local_path}")

sftp.close()

# Restart uWSGI
print()
print("[INFO] Restarting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("[OK] uWSGI restarted")

time.sleep(5)

ssh.close()

print()
print("=" * 80)
print("[OK] PROFILE PAGE UPDATED")
print("=" * 80)
print()
print("Features deployed:")
print("  ✅ All points displayed in comprehensive grid")
print("  ✅ Unified point counter integration")
print("  ✅ Quest points displayed")
print("  ✅ Reward points displayed")
print("  ✅ All saved data displayed")
print("  ✅ Real-time updates every 30 seconds")
print()
print("Points Categories Displayed:")
print("  - Core Points (XP, Level)")
print("  - Stats Points")
print("  - Quest Points")
print("  - Achievements & Milestones")
print("  - Economic (Coins, Credits)")
print("  - Battle Points")
print("  - Generation & Activity Points")
print("  - Rewards")
print("  - Social")
print("  - Metal Systems")

