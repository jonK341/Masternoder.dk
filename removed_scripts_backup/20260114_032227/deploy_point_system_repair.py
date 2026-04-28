#!/usr/bin/env python3
"""Deploy Point System Repair"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING POINT SYSTEM REPAIR")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/point_system_repair.py', '/var/www/html/vidgenerator/backend/services/point_system_repair.py'),
    ('backend/routes/point_system_repair_routes.py', '/var/www/html/vidgenerator/backend/routes/point_system_repair_routes.py'),
    ('vidgenerator/static/js/point-system-save-manager.js', '/var/www/html/vidgenerator/vidgenerator/static/js/point-system-save-manager.js'),
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

# Restart uWSGI
print()
print("[INFO] Restarting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("[OK] uWSGI restarted")

time.sleep(5)

# Restart Apache
print("[INFO] Restarting Apache...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart apache2.service")
stdout.read()
print("[OK] Apache restarted")

time.sleep(3)

# Check status
print("[INFO] Checking service status...")
stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi-vidgenerator.service apache2.service")
status = stdout.read().decode('utf-8')
print(f"Services: {status}")

ssh.close()

print()
print("=" * 80)
print("[OK] POINT SYSTEM REPAIR DEPLOYED")
print("=" * 80)
print()
print("Features:")
print("  ✅ Auto-save all points to DB and JSON")
print("  ✅ Repair lost counters")
print("  ✅ Progression triggers for all stats")
print("  ✅ Error handlers and event listeners")
print("  ✅ DOM watchers for point updates")
print("  ✅ Emergency save on page unload")
print()
print("Services restarted!")

"""Deploy Point System Repair"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING POINT SYSTEM REPAIR")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('backend/services/point_system_repair.py', '/var/www/html/vidgenerator/backend/services/point_system_repair.py'),
    ('backend/routes/point_system_repair_routes.py', '/var/www/html/vidgenerator/backend/routes/point_system_repair_routes.py'),
    ('vidgenerator/static/js/point-system-repair.js', '/var/www/html/vidgenerator/vidgenerator/static/js/point-system-repair.js'),
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
print("[OK] POINT SYSTEM REPAIR DEPLOYED")
print("=" * 80)
print()
print("Features:")
print("  ✅ Auto-repair lost counters")
print("  ✅ Auto-save every 30 seconds")
print("  ✅ Save on page unload")
print("  ✅ JSON file backup download")
print("  ✅ localStorage backup")
print("  ✅ Error handlers")
print("  ✅ Event listeners")
print("  ✅ DOM counter updates")
print()
print("API Endpoints:")
print("  POST /api/point-repair/repair/<user_id>")
print("  POST /api/point-repair/repair-counter/<user_id>/<counter_type>")
print("  GET  /api/point-repair/json-backup/<user_id>")

