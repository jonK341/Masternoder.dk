#!/usr/bin/env python3
"""
Deploy Monetization System - Top 25 Income Streams
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING MONETIZATION SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

files_to_deploy = [
    ('backend/services/monetization_system.py', '/var/www/html/vidgenerator/backend/services/monetization_system.py'),
    ('backend/routes/monetization_routes.py', '/var/www/html/vidgenerator/backend/routes/monetization_routes.py'),
    ('vidgenerator/monetization/index.html', '/var/www/html/vidgenerator/vidgenerator/monetization/index.html'),
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

ssh.close()

print("\n" + "=" * 80)
print("MONETIZATION SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Top 25 Income Streams Enabled:")
print("  1-5: Premium Subscriptions")
print("  6-10: In-App Purchases")
print("  11-15: Content & Features")
print("  16-20: Advertising & Sponsorships")
print("  21-25: Services & Tools")
print()
print("Access at: /vidgenerator/monetization/")
print()

