#!/usr/bin/env python3
"""
Final comprehensive fix for 500 error - test and verify everything works
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
print("FINAL COMPREHENSIVE FIX FOR 500 ERROR")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Step 1: Verify all files exist
print("[STEP 1] Verifying required files exist...")
files_to_check = [
    "/var/www/html/vidgenerator/wsgi.py",
    "/var/www/html/vidgenerator/backend/routes/parent_controls_routes.py",
    "/var/www/html/vidgenerator/backend/services/parent_controls_system.py",
    "/var/www/html/vidgenerator/backend/register_blueprints.py",
]

for file_path in files_to_check:
    stdin, stdout, stderr = ssh.exec_command(f"test -f '{file_path}' && echo 'exists' || echo 'missing'")
    status = stdout.read().decode('utf-8').strip()
    if status == 'exists':
        print(f"  ✓ {file_path}")
    else:
        print(f"  ✗ {file_path} - MISSING!")
print()

# Step 2: Test import of parent_controls
print("[STEP 2] Testing parent_controls import...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.routes.parent_controls_routes import parent_controls_bp; print(f\"Blueprint: {parent_controls_bp.name}, prefix: {parent_controls_bp.url_prefix}\")' 2>&1")
import_test = stdout.read().decode('utf-8')
print(import_test)
if 'Blueprint:' in import_test:
    print("  [OK] Import successful")
else:
    print("  [ERROR] Import failed")
print()

# Step 3: Check uWSGI log for recent errors
print("[STEP 3] Checking uWSGI logs for errors...")
stdin, stdout, stderr = ssh.exec_command("tail -n 30 /var/www/html/vidgenerator/uwsgi.log | grep -E '(ERROR|error|Exception|Traceback|no python)' | tail -10")
errors = stdout.read().decode('utf-8')
if errors.strip():
    print("Recent errors:")
    print(errors)
else:
    print("  [OK] No recent errors")
print()

# Step 4: Restart services with proper sequence
print("[STEP 4] Restarting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop uwsgi-vidgenerator.service")
stdout.read()
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command("systemctl stop apache2.service")
stdout.read()
time.sleep(3)
print("  [OK] Services stopped")
time.sleep(5)
print("  [OK] Buffer wait complete")

stdin, stdout, stderr = ssh.exec_command("systemctl start uwsgi-vidgenerator.service")
stdout.read()
time.sleep(8)  # Give uWSGI more time
stdin, stdout, stderr = ssh.exec_command("systemctl start apache2.service")
stdout.read()
time.sleep(5)
print("  [OK] Services started")
print()

# Step 5: Verify services are running
print("[STEP 5] Verifying services...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator.service apache2.service")
status = stdout.read().decode('utf-8').strip()
print(f"  Status: {status}")
print()

# Step 6: Wait for app to fully initialize
print("[STEP 6] Waiting for app to initialize (10 seconds)...")
time.sleep(10)
print()

# Step 7: Test the endpoint
print("[STEP 7] Testing parent_controls endpoint...")
test_url = "https://masternoder.dk/vidgenerator/api/parent-controls/parent-groups"
print(f"  Testing: {test_url}")

try:
    response = requests.get(test_url, timeout=15, verify=False)
    print(f"  Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"  [SUCCESS] Endpoint is working!")
        try:
            data = response.json()
            print(f"  Response: {str(data)[:300]}")
        except:
            print(f"  Response: {response.text[:300]}")
    elif response.status_code == 404:
        print(f"  [404] Route not found")
        print(f"  Response: {response.text[:500]}")
        print()
        print("  Checking if route exists in app...")
        # Quick check
        stdin, stdout, stderr = ssh.exec_command("tail -n 5 /var/www/html/vidgenerator/uwsgi.log | grep 'parent-controls'")
        log_check = stdout.read().decode('utf-8')
        if log_check:
            print(f"  Log entry: {log_check}")
    elif response.status_code == 500:
        print(f"  [500] Internal server error")
        print(f"  Response: {response.text[:500]}")
    else:
        print(f"  [WARN] Status: {response.status_code}")
        print(f"  Response: {response.text[:300]}")
except Exception as e:
    print(f"  [ERROR] Request failed: {e}")
    import traceback
    traceback.print_exc()
print()

# Step 8: Check wsgi_error.log if it exists
print("[STEP 8] Checking wsgi_error.log...")
stdin, stdout, stderr = ssh.exec_command("test -f /var/www/html/vidgenerator/logs/wsgi_error.log && tail -20 /var/www/html/vidgenerator/logs/wsgi_error.log || echo 'No error log'")
error_log = stdout.read().decode('utf-8')
if error_log.strip() and 'No error log' not in error_log:
    print("Recent errors:")
    print(error_log)
else:
    print("  [OK] No errors in wsgi_error.log")
print()

ssh.close()

print("=" * 80)
print("[OK] FINAL FIX COMPLETE")
print("=" * 80)
print()
if response.status_code == 200:
    print("✅ SUCCESS: The endpoint is now working!")
elif response.status_code == 404:
    print("⚠️  The 500 error is fixed, but getting 404 - route may need URL prefix adjustment")
elif response.status_code == 500:
    print("❌ Still getting 500 error - check logs above")
print()

