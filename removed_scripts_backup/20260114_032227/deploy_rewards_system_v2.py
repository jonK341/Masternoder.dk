#!/usr/bin/env python3
"""Deploy Rewards System v2.0"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING REWARDS SYSTEM V2.0")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/rewards_system_v2.py', '/var/www/html/vidgenerator/backend/services/rewards_system_v2.py'),
    ('backend/routes/rewards_routes_v2.py', '/var/www/html/vidgenerator/backend/routes/rewards_routes_v2.py'),
    ('backend/services/unified_points_database.py', '/var/www/html/vidgenerator/backend/services/unified_points_database.py'),
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
print("[OK] REWARDS SYSTEM V2.0 DEPLOYED")
print("=" * 80)
print()
print("Features deployed:")
print("  ✅ Database persistence")
print("  ✅ Multiple reward types (14 types)")
print("  ✅ Daily/weekly/monthly rewards")
print("  ✅ Achievement rewards")
print("  ✅ Battle rewards")
print("  ✅ Video generation rewards")
print("  ✅ Social rewards")
print("  ✅ Streak rewards")
print("  ✅ Level-up rewards")
print("  ✅ Quest/mission rewards")
print("  ✅ Special event rewards")
print("  ✅ Reward tiers and rarities (6 rarities)")
print("  ✅ API routes")
print("  ✅ Integration with unified point system")
print()
print("API Endpoints:")
print("  - GET /api/rewards/v2/user/<user_id>")
print("  - POST /api/rewards/v2/claim/<user_id>/<reward_id>")
print("  - POST /api/rewards/v2/claim-all/<user_id>")
print("  - GET/POST /api/rewards/v2/daily/<user_id>")
print("  - GET/POST /api/rewards/v2/weekly/<user_id>")
print("  - GET/POST /api/rewards/v2/monthly/<user_id>")
print("  - POST /api/rewards/v2/battle/<user_id>")
print("  - POST /api/rewards/v2/generation/<user_id>")
print("  - POST /api/rewards/v2/level-up/<user_id>/<level>")
print("  - POST /api/rewards/v2/achievement/<user_id>")
print("  - POST /api/rewards/v2/streak/<user_id>")
print("  - POST /api/rewards/v2/create/<user_id>")
print("  - GET /api/rewards/v2/categories")
print("  - GET /api/rewards/v2/types")
print("  - GET /api/rewards/v2/rarities")

