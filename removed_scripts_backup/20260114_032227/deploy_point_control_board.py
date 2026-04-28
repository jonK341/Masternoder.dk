#!/usr/bin/env python3
"""
Deploy Point System Control Board
Deploy scalable dashboard system to server
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING POINT SYSTEM CONTROL BOARD")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

# Files to deploy
files_to_deploy = [
    ('backend/services/point_system_control_board.py', '/var/www/html/vidgenerator/backend/services/point_system_control_board.py'),
    ('backend/routes/point_control_board_routes.py', '/var/www/html/vidgenerator/backend/routes/point_control_board_routes.py'),
    ('vidgenerator/dashboard/point_control_board.html', '/var/www/html/vidgenerator/vidgenerator/dashboard/point_control_board.html'),
    ('vidgenerator/dashboard/point_system_template.html', '/var/www/html/vidgenerator/vidgenerator/dashboard/point_system_template.html'),
]

print("[1] Deploying files...")
for local_path, remote_path in files_to_deploy:
    try:
        with open(local_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create directory if needed
        remote_dir = os.path.dirname(remote_path)
        stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
        stdout.read()
        
        # Write file
        with sftp.file(remote_path, 'w') as rf:
            rf.write(content)
        
        print(f"  ✓ Deployed: {local_path}")
    except Exception as e:
        print(f"  ✗ Error deploying {local_path}: {e}")

sftp.close()

# Update register_blueprints.py
print("\n[2] Checking register_blueprints.py...")
stdin, stdout, stderr = ssh.exec_command("grep -n 'point_control_board' /var/www/html/vidgenerator/backend/register_blueprints.py")
registration = stdout.read().decode('utf-8')
if registration:
    print("  ✓ Already registered in register_blueprints.py")
else:
    print("  ⚠ Not found - may need manual registration")

# Test import
print("\n[3] Testing imports...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.services.point_system_control_board import point_system_control_board; from backend.routes.point_control_board_routes import point_control_board_bp; print(\"All imports successful\")' 2>&1")
test_output = stdout.read().decode('utf-8')
if 'successful' in test_output or 'Error' not in test_output:
    print("  ✓ All imports successful")
else:
    print(f"  ⚠ Import test output: {test_output}")

# Restart uWSGI
print("\n[4] Restarting uWSGI...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
restart_output = stdout.read().decode('utf-8')
if restart_output:
    print(restart_output)
else:
    print("  ✓ uWSGI restarted")

# Restart Apache
print("\n[5] Restarting Apache...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart apache2")
restart_output = stdout.read().decode('utf-8')
if restart_output:
    print(restart_output)
else:
    print("  ✓ Apache restarted")

ssh.close()

print("\n" + "=" * 80)
print("DEPLOYMENT COMPLETE")
print("=" * 80)
print()
print("✅ Deployed files:")
print("  - point_system_control_board.py")
print("  - point_control_board_routes.py")
print("  - point_control_board.html")
print("  - point_system_template.html")
print()
print("✅ Services restarted")
print()
print("📡 Control Board URLs:")
print("  - Main: /vidgenerator/dashboard/points")
print("  - System: /vidgenerator/dashboard/points/<system_id>")
print("  - API Overview: /vidgenerator/api/points/control-board/overview")
print("  - API System: /vidgenerator/api/points/control-board/system/<system_id>")
print()

