#!/usr/bin/env python3
"""
Restore virtualenv and check uWSGI logs for exact error
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("RESTORING VIRTUALENV AND CHECKING LOGS")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Restore virtualenv
print("[1] Restoring virtualenv setting...")
stdin, stdout, stderr = ssh.exec_command("sed -i 's/^#virtualenv =/virtualenv =/' /var/www/html/vidgenerator/uwsgi.ini")
stdin, stdout, stderr = ssh.exec_command("grep -i virtualenv /var/www/html/vidgenerator/uwsgi.ini")
venv_restored = stdout.read().decode('utf-8')
print(venv_restored)
print()

# Check the very latest uWSGI log entries
print("[2] Latest uWSGI log entries (last 50 lines)...")
stdin, stdout, stderr = ssh.exec_command("tail -n 50 /var/www/html/vidgenerator/uwsgi.log")
latest_logs = stdout.read().decode('utf-8')
print(latest_logs)
print()

# Check for wsgi messages
print("[3] Checking for wsgi messages...")
stdin, stdout, stderr = ssh.exec_command("grep -i '\\[wsgi\\]' /var/www/html/vidgenerator/uwsgi.log | tail -10")
wsgi_messages = stdout.read().decode('utf-8')
if wsgi_messages.strip():
    print(wsgi_messages)
else:
    print("No [wsgi] messages found - this means wsgi.py might not be executing")
print()

ssh.close()

print("=" * 80)
print("[OK] RESTORE AND CHECK COMPLETE")
print("=" * 80)
print()
print("The issue is that uWSGI can't find the application variable.")
print("This suggests wsgi.py might not be completing execution, or")
print("the application variable isn't being set in the module namespace.")
print("The traceback from two_phase_api.py might be preventing the module from loading.")

