#!/usr/bin/env python3
"""
Restart Flask engine (uWSGI) and Apache, then test parent_controls URL
"""
import paramiko
import os
import sys
import time
import requests

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("RESTARTING FLASK ENGINE AND APACHE, THEN TESTING URL")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Step 1: Stop services
print("[STEP 1] Stopping services...")
print("  Stopping uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop uwsgi-vidgenerator.service")
stdout.read()
time.sleep(2)

print("  Stopping Apache...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop apache2.service")
stdout.read()
time.sleep(2)
print("  [OK] Services stopped")
print()

# Step 2: Buffer wait
print("[STEP 2] Buffer wait (5 seconds)...")
time.sleep(5)
print()

# Step 3: Start services
print("[STEP 3] Starting services...")
print("  Starting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl start uwsgi-vidgenerator.service")
stdout.read()
time.sleep(3)

print("  Starting Apache...")
stdin, stdout, stderr = ssh.exec_command("systemctl start apache2.service")
stdout.read()
time.sleep(3)
print("  [OK] Services started")
print()

# Step 4: Verify services
print("[STEP 4] Verifying services...")
time.sleep(5)

stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator.service")
uwsgi_status = stdout.read().decode('utf-8').strip()
print(f"  uWSGI status: {uwsgi_status}")

stdin, stdout, stderr = ssh.exec_command("systemctl is-active apache2.service")
apache_status = stdout.read().decode('utf-8').strip()
print(f"  Apache status: {apache_status}")
print()

# Step 5: Check for errors
print("[STEP 5] Checking for errors...")
stdin, stdout, stderr = ssh.exec_command("tail -n 20 /var/log/uwsgi/vidgenerator.log | grep -i error || echo 'No recent errors in uWSGI logs'")
uwsgi_errors = stdout.read().decode('utf-8')
if 'No recent errors' not in uwsgi_errors:
    print("  [WARN] Recent uWSGI errors:")
    print(f"  {uwsgi_errors}")
else:
    print("  [OK] No recent errors in uWSGI logs")

stdin, stdout, stderr = ssh.exec_command("tail -n 10 /var/log/apache2/error.log | grep -i error || echo 'No recent errors in Apache logs'")
apache_errors = stdout.read().decode('utf-8')
if 'No recent errors' not in apache_errors:
    print("  [WARN] Recent Apache errors:")
    print(f"  {apache_errors}")
else:
    print("  [OK] No recent errors in Apache logs")
print()

ssh.close()

# Step 6: Test the URL
print("[STEP 6] Testing parent_controls URL...")
print("  Waiting 3 seconds for services to fully initialize...")
time.sleep(3)

test_urls = [
    "https://masternoder.dk/vidgenerator/api/parent-controls/parent-groups",
    "https://masternoder.dk/api/parent-controls/parent-groups",
]

for url in test_urls:
    print(f"\n  Testing: {url}")
    try:
        response = requests.get(url, timeout=10, verify=False)
        print(f"    Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"    [OK] URL is working!")
            try:
                data = response.json()
                print(f"    Response: {str(data)[:200]}...")
            except:
                print(f"    Response: {response.text[:200]}...")
        elif response.status_code == 500:
            print(f"    [ERROR] Internal Server Error (500)")
            print(f"    Response: {response.text[:500]}")
        else:
            print(f"    [WARN] Status: {response.status_code}")
            print(f"    Response: {response.text[:200]}...")
    except requests.exceptions.RequestException as e:
        print(f"    [ERROR] Request failed: {e}")
    except Exception as e:
        print(f"    [ERROR] Unexpected error: {e}")

print()
print("=" * 80)
print("[OK] RESTART AND TEST COMPLETE")
print("=" * 80)

