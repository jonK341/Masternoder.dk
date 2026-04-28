#!/usr/bin/env python3
"""
Deploy parent_controls files to server
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING PARENT_CONTROLS FILES TO SERVER")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy parent_controls_routes.py
print("[1] Deploying parent_controls_routes.py...")
try:
    with open('backend/routes/parent_controls_routes.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    remote_path = '/var/www/html/vidgenerator/backend/routes/parent_controls_routes.py'
    with sftp.file(remote_path, 'w') as f:
        f.write(content)
    print(f"  [OK] Deployed to {remote_path}")
except Exception as e:
    print(f"  [ERROR] Failed to deploy parent_controls_routes.py: {e}")
    import traceback
    traceback.print_exc()
print()

# Deploy parent_controls_system.py
print("[2] Deploying parent_controls_system.py...")
try:
    with open('backend/services/parent_controls_system.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    remote_path = '/var/www/html/vidgenerator/backend/services/parent_controls_system.py'
    with sftp.file(remote_path, 'w') as f:
        f.write(content)
    print(f"  [OK] Deployed to {remote_path}")
except Exception as e:
    print(f"  [ERROR] Failed to deploy parent_controls_system.py: {e}")
    import traceback
    traceback.print_exc()
print()

# Deploy updated register_blueprints.py (in case it wasn't deployed)
print("[3] Deploying register_blueprints.py...")
try:
    with open('backend/register_blueprints.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    remote_path = '/var/www/html/vidgenerator/backend/register_blueprints.py'
    with sftp.file(remote_path, 'w') as f:
        f.write(content)
    print(f"  [OK] Deployed to {remote_path}")
except Exception as e:
    print(f"  [ERROR] Failed to deploy register_blueprints.py: {e}")
    import traceback
    traceback.print_exc()
print()

sftp.close()

# Verify files exist
print("[4] Verifying files exist on server...")
stdin, stdout, stderr = ssh.exec_command("ls -la /var/www/html/vidgenerator/backend/routes/parent_controls_routes.py /var/www/html/vidgenerator/backend/services/parent_controls_system.py 2>&1")
verification = stdout.read().decode('utf-8')
print(verification)
print()

# Test import
print("[5] Testing import on server...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.routes.parent_controls_routes import parent_controls_bp; print(\"Import successful\")' 2>&1")
import_test = stdout.read().decode('utf-8')
import_test_err = stderr.read().decode('utf-8')
print("Import test output:")
print(import_test)
if import_test_err:
    print("Import test errors:")
    print(import_test_err)
print()

# Restart services
print("[6] Restarting services...")
import time

# Stop services
print("  Stopping services...")
stdin, stdout, stderr = ssh.exec_command("systemctl stop uwsgi-vidgenerator.service")
stdout.read()
time.sleep(2)
stdin, stdout, stderr = ssh.exec_command("systemctl stop apache2.service")
stdout.read()
time.sleep(2)

# Wait
print("  Waiting 5 seconds...")
time.sleep(5)

# Start services
print("  Starting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl start uwsgi-vidgenerator.service")
stdout.read()
time.sleep(3)
stdin, stdout, stderr = ssh.exec_command("systemctl start apache2.service")
stdout.read()
time.sleep(3)

# Verify
print("  Verifying services...")
time.sleep(5)
stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator.service apache2.service")
status = stdout.read().decode('utf-8')
print(f"  Status: {status.strip()}")
print()

ssh.close()

print("=" * 80)
print("[OK] PARENT_CONTROLS FILES DEPLOYED AND SERVICES RESTARTED")
print("=" * 80)

