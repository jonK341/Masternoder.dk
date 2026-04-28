#!/usr/bin/env python3
"""Deploy Progression System"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING PROGRESSION SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/progression_system.py', '/var/www/html/vidgenerator/backend/services/progression_system.py'),
    ('backend/routes/progression_routes.py', '/var/www/html/vidgenerator/backend/routes/progression_routes.py'),
    ('vidgenerator/static/js/progression-display.js', '/var/www/html/vidgenerator/vidgenerator/static/js/progression-display.js'),
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
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
print("[OK] PROGRESSION SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Features:")
print("  ✅ Points and Level Progression across all sites")
print("  ✅ 8 Category Progressions (Main, Battle, Social, Generation, Quest, Achievement, Rights, Shop)")
print("  ✅ Real-time Progress Bars")
print("  ✅ Level Names and Titles")
print("  ✅ Progress Percentages")
print("  ✅ Auto-updating Widgets")
print()
print("API Endpoints:")
print("  GET /api/progression/all/<user_id> - Get all progressions")
print("  GET /api/progression/<user_id>/<category> - Get category progression")
print()
print("Frontend:")
print("  ✅ progression-display.js - Auto-loads on all pages")
print("  ✅ Progression widgets with progress bars")
print("  ✅ Category progression displays")

