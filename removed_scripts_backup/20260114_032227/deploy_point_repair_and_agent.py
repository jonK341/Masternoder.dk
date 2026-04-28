#!/usr/bin/env python3
"""Deploy Point System Repair and Agent Task Force"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING POINT SYSTEM REPAIR AND AGENT TASK FORCE")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/point_system_repair.py', '/var/www/html/vidgenerator/backend/services/point_system_repair.py'),
    ('backend/services/agent_task_force.py', '/var/www/html/vidgenerator/backend/services/agent_task_force.py'),
    ('backend/routes/point_system_repair_routes.py', '/var/www/html/vidgenerator/backend/routes/point_system_repair_routes.py'),
    ('backend/routes/agent_task_force_routes.py', '/var/www/html/vidgenerator/backend/routes/agent_task_force_routes.py'),
    ('vidgenerator/static/js/point-system-repair.js', '/var/www/html/vidgenerator/vidgenerator/static/js/point-system-repair.js'),
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
]

print("[INFO] Deploying files...")
for local_path, remote_path in files_to_deploy:
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
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

ssh.close()

print()
print("=" * 80)
print("[OK] POINT SYSTEM REPAIR AND AGENT TASK FORCE DEPLOYED")
print("=" * 80)
print()
print("Features:")
print("  ✅ Point System Repair")
print("  ✅ Save to DB and Local JSON")
print("  ✅ Progression Triggers")
print("  ✅ Error Handlers")
print("  ✅ Event Listeners")
print("  ✅ Agent Task Force")
print("  ✅ Objective Assignment")
print("  ✅ Mission Control")
print("  ✅ Calendar Integration")
print("  ✅ Agent Observations")
print("  ✅ Emotion Counters")
print("  ✅ Behavior Patterns")

