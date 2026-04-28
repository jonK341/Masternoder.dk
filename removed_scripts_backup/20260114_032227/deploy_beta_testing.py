#!/usr/bin/env python3
"""
Deploy Beta Testing System
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING BETA TESTING SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

files_to_deploy = [
    ('backend/services/beta_testing_system.py', '/var/www/html/vidgenerator/backend/services/beta_testing_system.py'),
    ('backend/routes/beta_testing_routes.py', '/var/www/html/vidgenerator/backend/routes/beta_testing_routes.py'),
    ('vidgenerator/beta_testing/index.html', '/var/www/html/vidgenerator/vidgenerator/beta_testing/index.html'),
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
]

print("[1] Deploying files...")
for local_path, remote_path in files_to_deploy:
    try:
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
            stdout.read()
            
            with sftp.file(remote_path, 'w') as rf:
                rf.write(content)
            
            print(f"  [OK] Deployed: {local_path}")
        else:
            print(f"  [SKIP] File not found: {local_path}")
    except Exception as e:
        print(f"  [ERROR] Error deploying {local_path}: {e}")

sftp.close()

print("\n[2] Restarting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi && sleep 2 && systemctl restart apache2")
print("  [OK] Services restarted")

print("\n[3] Creating initial beta test...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 create_initial_beta_test.py 2>&1")
output = stdout.read().decode('utf-8')
print(output)

ssh.close()

print("\n" + "=" * 80)
print("BETA TESTING SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Beta testing is now available at:")
print("  - /vidgenerator/beta_testing/")
print()
print("API Endpoints:")
print("  - POST /api/beta-testing/create")
print("  - POST /api/beta-testing/register/<test_id>")
print("  - POST /api/beta-testing/feedback/<test_id>")
print("  - GET /api/beta-testing/tests")
print()

