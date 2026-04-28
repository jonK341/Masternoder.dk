#!/usr/bin/env python3
"""Final URL test and continue with TODO list"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("FINAL URL TEST AND TODO LIST CONTINUATION")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Deploy the fix
print("[INFO] Deploying activity_points_page registration fix...")
sftp = ssh.open_sftp()

# Read local file
with open('backend/register_blueprints.py', 'r', encoding='utf-8') as f:
    local_content = f.read()

# Write to server
with sftp.file('/var/www/html/vidgenerator/backend/register_blueprints.py', 'w') as f:
    f.write(local_content)

sftp.close()
print("  [OK] Deployed fix")

# Restart uWSGI
print()
print("[INFO] Restarting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("[OK] uWSGI restarted")

time.sleep(5)

# Final comprehensive test
print()
print("[INFO] Final comprehensive URL test...")
print("-" * 80)

all_urls = [
    "/vidgenerator/",
    "/vidgenerator/battle/",
    "/vidgenerator/dashboard/",
    "/vidgenerator/generator/",
    "/vidgenerator/social/",
    "/vidgenerator/stats/",
    "/vidgenerator/profile/",
    "/vidgenerator/game/",
    "/vidgenerator/gallery/",
    "/vidgenerator/aggregator/",
    "/vidgenerator/metal/",
    "/vidgenerator/theme-points/",
    "/vidgenerator/activity-points/",
    "/vidgenerator/chat/",
    "/vidgenerator/shop/",
    "/api/activity-points/test",
    "/vidgenerator/api/activity-points/test",
    "/api/battle/intelligence/test",
    "/vidgenerator/api/battle/intelligence/test",
]

working = 0
broken = []

for url in all_urls:
    stdin, stdout, stderr = ssh.exec_command(f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:5000{url}")
    status = stdout.read().decode('utf-8', errors='ignore').strip()
    if status == '200':
        print(f"[OK] {url}")
        working += 1
    else:
        print(f"[{status}] {url}")
        broken.append((url, status))

# Summary
print()
print("=" * 80)
print("FINAL SUMMARY")
print("=" * 80)
print(f"Working URLs: {working}/{len(all_urls)}")
print(f"Broken URLs: {len(broken)}")

if broken:
    print()
    print("Broken URLs:")
    for url, status in broken:
        print(f"  - {url}: HTTP {status}")

# Continue with TODO list
print()
print("=" * 80)
print("CONTINUING WITH TODO LIST")
print("=" * 80)
print()

# Read TODO list
todo_file = "BATTLE_INTELLIGENCE_TODO.md"
if os.path.exists(todo_file):
    with open(todo_file, 'r', encoding='utf-8') as f:
        todo_content = f.read()
    
    # Extract high-priority items
    lines = todo_content.split('\n')
    high_priority = []
    for line in lines:
        if '- [ ]' in line and ('Priority 1' in line or 'Phase 1' in line or 'Foundation' in line):
            high_priority.append(line.strip())
    
    print(f"[INFO] Found {len(high_priority)} high-priority TODO items")
    print()
    print("High-Priority Items:")
    for item in high_priority[:10]:
        print(f"  - {item}")
    
    print()
    print("[INFO] Ready to implement TODO items")
else:
    print("[WARN] TODO file not found")

ssh.close()

print()
print("=" * 80)
print("[OK] COMPLETE")
print("=" * 80)


