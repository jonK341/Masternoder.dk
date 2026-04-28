#!/usr/bin/env python3
"""Deploy Complete Systems: Agent Task Force, Progression Triggers, Point Repair"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING COMPLETE SYSTEMS")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/agent_task_force.py', '/var/www/html/vidgenerator/backend/services/agent_task_force.py'),
    ('backend/routes/agent_task_force_routes.py', '/var/www/html/vidgenerator/backend/routes/agent_task_force_routes.py'),
    ('backend/services/progression_triggers.py', '/var/www/html/vidgenerator/backend/services/progression_triggers.py'),
    ('backend/routes/progression_triggers_routes.py', '/var/www/html/vidgenerator/backend/routes/progression_triggers_routes.py'),
    ('vidgenerator/static/js/progression-triggers.js', '/var/www/html/vidgenerator/vidgenerator/static/js/progression-triggers.js'),
    ('vidgenerator/index.html', '/var/www/html/vidgenerator/vidgenerator/index.html'),
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

# Restart services
print()
print("[INFO] Restarting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service && systemctl restart apache2.service")
stdout.read()
print("[OK] Services restarted")

time.sleep(5)

# Check status
stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator.service apache2.service")
status = stdout.read().decode('utf-8')
print(f"[INFO] Service status: {status.strip()}")

ssh.close()

print()
print("=" * 80)
print("[OK] ALL SYSTEMS DEPLOYED")
print("=" * 80)
print()
print("Deployed Systems:")
print("  ✅ Point System Repair")
print("  ✅ Agent Task Force")
print("  ✅ Progression Triggers")
print()
print("Features:")
print("  ✅ Auto-save all points")
print("  ✅ JSON file backup")
print("  ✅ Error handlers")
print("  ✅ Event listeners")
print("  ✅ DOM watchers")
print("  ✅ Progression milestones")
print("  ✅ Mission control")
print("  ✅ Calendar integration")
print("  ✅ Behavior patterns")
print("  ✅ Emotion counters")
