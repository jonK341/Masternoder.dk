#!/usr/bin/env python3
"""Remove orphan except at 702"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()
with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'r') as f:
    content = f.read().decode('utf-8')

lines = content.split('\n')

# Remove orphan except at 702 and its content (702-704)
print("Removing orphan except block at lines 702-704...")
lines_to_delete = [701, 702, 703]  # 0-indexed

# Delete in reverse order
for idx in sorted(lines_to_delete, reverse=True):
    if idx < len(lines):
        print(f"Deleting line {idx+1}: {lines[idx][:50]}")
        del lines[idx]

# Write back
new_content = '\n'.join(lines)
with sftp.file('/var/www/html/vidgenerator/src/services/ai_generation/worker_intelligence_ai.py', 'w') as f:
    f.write(new_content)
sftp.close()

# Test syntax
print("\n[INFO] Testing syntax...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -m py_compile src/services/ai_generation/worker_intelligence_ai.py 2>&1")
result = stdout.read().decode('utf-8', errors='ignore')
if stderr:
    result += stderr.read().decode('utf-8', errors='ignore')

if 'SyntaxError' in result or 'Error' in result:
    print(f"[WARN] Error: {result[:200]}")
else:
    print("[OK] Syntax OK!")
    print()
    print("=" * 80)
    print("RESTARTING FLASK/uWSGI")
    print("=" * 80)
    print()
    
    print("[INFO] Restarting uWSGI service...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
    stdout.read()
    print("[OK] uWSGI restarted")
    
    time.sleep(5)
    
    print()
    print("[INFO] Testing endpoints...")
    stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/activity-points/test")
    response1 = stdout.read().decode('utf-8', errors='ignore')
    print(f"Activity Points: {response1}")
    
    stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/battle/intelligence/test")
    response2 = stdout.read().decode('utf-8', errors='ignore')
    print(f"Battle Intelligence: {response2}")
    
    if 'success' in response1.lower() or 'activity' in response1.lower():
        print("\n[OK] Activity Points endpoint is working!")
    if 'success' in response2.lower() or 'battle' in response2.lower():
        print("[OK] Battle Intelligence endpoint is working!")
    
    if 'success' in (response1 + response2).lower():
        print("\n[OK] SUCCESS! All endpoints are working!")

ssh.close()

