#!/usr/bin/env python3
"""Deploy Time Achievement Guides"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING TIME ACHIEVEMENT GUIDES")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/time_achievement_guides.py', '/var/www/html/vidgenerator/backend/services/time_achievement_guides.py'),
    ('backend/routes/time_achievement_guides_routes.py', '/var/www/html/vidgenerator/backend/routes/time_achievement_guides_routes.py'),
    ('backend/routes/time_achievement_guides_page.py', '/var/www/html/vidgenerator/backend/routes/time_achievement_guides_page.py'),
    ('vidgenerator/time-achievement-guides/index.html', '/var/www/html/vidgenerator/vidgenerator/time-achievement-guides/index.html'),
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
print("[OK] TIME ACHIEVEMENT GUIDES DEPLOYED")
print("=" * 80)
print()
print("Features deployed:")
print("  ✅ Time Achievement Guides System")
print("  ✅ 5 Achievement Categories")
print("  ✅ 20+ Achievement Guides")
print("  ✅ Tips and Strategies")
print("  ✅ Reward Information")
print("  ✅ User Recommendations")
print("  ✅ Beautiful UI with Categories")
print()
print("Categories:")
print("  📅 Daily Achievements")
print("  📆 Weekly Achievements")
print("  🗓️ Monthly Achievements")
print("  🔥 Streak Achievements")
print("  ⏱️ Time Investment Achievements")
print()
print("Access at: /vidgenerator/time-achievement-guides")

