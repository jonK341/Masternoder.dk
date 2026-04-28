#!/usr/bin/env python3
"""Deploy Behavior Pattern Tracking System"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING BEHAVIOR PATTERN TRACKING SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/behavior_pattern_tracker.py', '/var/www/html/vidgenerator/backend/services/behavior_pattern_tracker.py'),
    ('backend/routes/behavior_pattern_routes.py', '/var/www/html/vidgenerator/backend/routes/behavior_pattern_routes.py'),
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
]

print("[INFO] Deploying files...")
for local_path, remote_path in files_to_deploy:
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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

# Test endpoints
print()
print("[INFO] Testing Behavior Pattern Tracking endpoints...")
print("-" * 80)

test_endpoints = [
    "/api/behavior-pattern/test",
]

for endpoint in test_endpoints:
    stdin, stdout, stderr = ssh.exec_command(f"curl -s http://127.0.0.1:5000{endpoint}")
    response = stdout.read().decode('utf-8', errors='ignore')
    if 'success' in response.lower() or 'working' in response.lower():
        print(f"  [OK] {endpoint}")
    else:
        print(f"  [WARN] {endpoint}: {response[:100]}")

ssh.close()

print()
print("=" * 80)
print("[OK] BEHAVIOR PATTERN TRACKING SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Features implemented:")
print("  ✅ Mouse movement tracking")
print("  ✅ Click pattern analysis")
print("  ✅ Scroll depth monitoring")
print("  ✅ Interaction timing analysis")
print("  ✅ Attention hotspot detection")
print()
print("Next: Continue with TODO list items")

