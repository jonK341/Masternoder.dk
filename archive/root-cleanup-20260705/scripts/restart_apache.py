#!/usr/bin/env python3
"""
Restart Apache webserver
"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("RESTARTING APACHE WEBSERVER")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Check current status
print("[1] Checking Apache current status...")
stdin, stdout, stderr = ssh.exec_command("systemctl status apache2.service --no-pager | head -10")
status = stdout.read().decode('utf-8')
print(status)
print()

# Restart Apache
print("[2] Restarting Apache service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart apache2.service 2>&1")
restart_output = stdout.read().decode('utf-8')
restart_errors = stderr.read().decode('utf-8')
if restart_output:
    print(restart_output)
if restart_errors:
    print(f"Restart errors: {restart_errors}")
print()

# Wait for Apache to start
print("[3] Waiting 3 seconds for Apache to start...")
time.sleep(3)
print()

# Verify Apache is running
print("[4] Verifying Apache is active...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active apache2.service")
apache_status = stdout.read().decode('utf-8').strip()
if apache_status == 'active':
    print(f"  [OK] Apache is {apache_status}")
else:
    print(f"  [WARN] Apache status: {apache_status}")
print()

# Check for any errors
print("[5] Checking Apache error log for recent errors...")
stdin, stdout, stderr = ssh.exec_command("tail -n 10 /var/log/apache2/error.log | grep -i error || echo 'No recent errors'")
errors = stdout.read().decode('utf-8')
print(errors)
print()

ssh.close()

print("=" * 80)
print("[OK] APACHE WEBSERVER RESTARTED")
print("=" * 80)

