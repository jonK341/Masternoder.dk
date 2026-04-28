#!/usr/bin/env python3
"""Deploy Rights and Law System"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING RIGHTS AND LAW SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/rights_law_system.py', '/var/www/html/vidgenerator/backend/services/rights_law_system.py'),
    ('backend/routes/rights_law_routes.py', '/var/www/html/vidgenerator/backend/routes/rights_law_routes.py'),
    ('backend/routes/rights_law_page.py', '/var/www/html/vidgenerator/backend/routes/rights_law_page.py'),
    ('vidgenerator/rights-law/index.html', '/var/www/html/vidgenerator/vidgenerator/rights-law/index.html'),
    ('backend/services/unified_point_counter.py', '/var/www/html/vidgenerator/backend/services/unified_point_counter.py'),
    ('backend/services/point_connection_system.py', '/var/www/html/vidgenerator/backend/services/point_connection_system.py'),
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
]

print("[INFO] Deploying files...")
for local_path, remote_path in files_to_deploy:
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create directory if needed
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.read()
        
        with sftp.file(remote_path, 'w') as f:
            f.write(content)
        print(f"  [OK] Deployed {local_path}")
    else:
        print(f"  [WARN] File not found: {local_path}")

sftp.close()

# Restart uWSGI
print()
print("[INFO] Restarting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("[OK] uWSGI restarted")

time.sleep(5)

ssh.close()

print()
print("=" * 80)
print("[OK] RIGHTS AND LAW SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Features:")
print("  ✅ Rights and Law Paragraphs System")
print("  ✅ 5 Categories with 20+ Paragraphs")
print("  ✅ Unified Points Integration")
print("  ✅ Discussion Groups in Socials")
print("  ✅ Points for Reading Paragraphs")
print("  ✅ Points for Creating/Joining Groups")
print("  ✅ Points for Discussions and Replies")
print()
print("Categories:")
print("  📜 Data Protection Rights")
print("  📜 Intellectual Property Rights")
print("  📜 User Rights")
print("  📜 Content Rights")
print("  📜 Platform Rights")
print()
print("API Endpoints:")
print("  GET  /api/rights-law/paragraphs")
print("  GET  /api/rights-law/paragraphs/category/<category>")
print("  GET  /api/rights-law/paragraphs/<paragraph_id>")
print("  POST /api/rights-law/paragraphs/<paragraph_id>/read")
print("  GET  /api/rights-law/user/<user_id>/rights")
print("  GET  /api/rights-law/groups")
print("  POST /api/rights-law/groups/create")
print("  POST /api/rights-law/groups/<group_id>/join")
print("  POST /api/rights-law/groups/<group_id>/discussions/create")
print("  POST /api/rights-law/discussions/<discussion_id>/reply")

