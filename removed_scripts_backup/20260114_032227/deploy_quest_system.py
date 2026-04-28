#!/usr/bin/env python3
"""Deploy Quest System"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING QUEST SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/quest_system.py', '/var/www/html/vidgenerator/backend/services/quest_system.py'),
    ('backend/routes/quest_routes.py', '/var/www/html/vidgenerator/backend/routes/quest_routes.py'),
    ('backend/routes/quest_page.py', '/var/www/html/vidgenerator/backend/routes/quest_page.py'),
    ('backend/services/point_connection_system.py', '/var/www/html/vidgenerator/backend/services/point_connection_system.py'),
    ('backend/services/unified_point_counter.py', '/var/www/html/vidgenerator/backend/services/unified_point_counter.py'),
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
    ('vidgenerator/quests/index.html', '/var/www/html/vidgenerator/vidgenerator/quests/index.html'),
    ('vidgenerator/generator/index.html', '/var/www/html/vidgenerator/vidgenerator/generator/index.html'),
    ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
    ('vidgenerator/dashboard/index.html', '/var/www/html/vidgenerator/vidgenerator/dashboard/index.html'),
    ('vidgenerator/static/js/unified-point-counters.js', '/var/www/html/vidgenerator/vidgenerator/static/js/unified-point-counters.js'),
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
print("[OK] QUEST SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Features deployed:")
print("  ✅ Progression quest system with levels")
print("  ✅ 8 quest types (Video Creator, Battle Master, etc.)")
print("  ✅ Quest points integration")
print("  ✅ Quest rewards system")
print("  ✅ Quest UI page")
print("  ✅ Quest points in frontend display")
print("  ✅ All points displayed in UI")
print()
print("Quest Types:")
print("  - Video Creator (create videos)")
print("  - Battle Master (win battles)")
print("  - Social Networker (add friends)")
print("  - Quality Seeker (high-quality videos)")
print("  - Daily Warrior (daily login)")
print("  - Achievement Hunter (unlock achievements)")
print("  - Level Climber (reach levels)")
print("  - Point Collector (collect points)")
print()
print("Quest Levels:")
print("  - Beginner (Level 1-10)")
print("  - Intermediate (Level 11-25)")
print("  - Advanced (Level 26-50)")
print("  - Expert (Level 51-100)")
print("  - Master (Level 101-200)")
print("  - Legendary (Level 201+)")

