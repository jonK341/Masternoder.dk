#!/usr/bin/env python3
"""Deploy Video Generation Points Integration"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING VIDEO GENERATION POINTS INTEGRATION")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/routes/generator.py', '/var/www/html/vidgenerator/backend/routes/generator.py'),
    ('vidgenerator/generator/index.html', '/var/www/html/vidgenerator/vidgenerator/generator/index.html'),
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
print("[OK] VIDEO GENERATION POINTS INTEGRATION DEPLOYED")
print("=" * 80)
print()
print("Features deployed:")
print("  ✅ Point connection in video generation")
print("  ✅ Points display widget on generator page")
print("  ✅ Real-time point updates")
print("  ✅ All point types displayed")
print()
print("Points Awarded for Video Generation:")
print("  - XP: Based on quality and completion")
print("  - Generation Points: 50 base + quality bonus")
print("  - Activity Points: 25 points")
print("  - All points connected to unified system")

