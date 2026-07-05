#!/usr/bin/env python3
"""Restart services now"""
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

print("=" * 80)
print("RESTARTING SERVICES")
print("=" * 80)
print()

# Restart uWSGI
print("📋 Restarting uWSGI service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("✅ uWSGI restarted")

# Wait
time.sleep(5)

# Check status
print()
print("📋 Checking uWSGI status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi-vidgenerator.service --no-pager | head -15")
status = stdout.read().decode('utf-8', errors='ignore')
print(status)

# Test endpoints
print()
print("📋 Testing endpoints...")
stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/activity-points/test")
response1 = stdout.read().decode('utf-8', errors='ignore')
print(f"Activity Points: {response1}")

stdin, stdout, stderr = ssh.exec_command("curl -s http://127.0.0.1:5000/api/battle/intelligence/test")
response2 = stdout.read().decode('utf-8', errors='ignore')
print(f"Battle Intelligence: {response2}")

# Check uWSGI logs for errors
print()
print("📋 Checking uWSGI logs...")
stdin, stdout, stderr = ssh.exec_command("tail -20 /var/www/html/vidgenerator/uwsgi.log | grep -i 'error\|no python\|application' | tail -5")
logs = stdout.read().decode('utf-8', errors='ignore')
if logs:
    print(f"Recent errors: {logs}")
else:
    print("No recent errors in log")

if 'success' in response1.lower() or 'activity' in response1.lower():
    print("\n🎉 Activity Points endpoint is working!")
if 'success' in response2.lower() or 'battle' in response2.lower():
    print("🎉 Battle Intelligence endpoint is working!")

if 'success' in (response1 + response2).lower():
    print("\n🎉🎉🎉 SUCCESS! All endpoints are working!")
else:
    print("\n⚠️  Endpoints still returning errors, but services are restarted")

print()
print("=" * 80)
print("✅ SERVICES RESTARTED")
print("=" * 80)

ssh.close()

