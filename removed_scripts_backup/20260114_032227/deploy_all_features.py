#!/usr/bin/env python3
"""
Deploy All Latest Features
- Agent Listeners/Handlers
- Advanced Calculator
- Dashboards
- JSON Encryption
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING ALL LATEST FEATURES")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

# Files to deploy
files_to_deploy = [
    # Agent Listeners/Handlers
    ('src/db/models_agent_listeners.py', '/var/www/html/vidgenerator/src/db/models_agent_listeners.py'),
    ('backend/services/agent_listeners_handlers_system.py', '/var/www/html/vidgenerator/backend/services/agent_listeners_handlers_system.py'),
    ('backend/routes/agent_listeners_handlers_routes.py', '/var/www/html/vidgenerator/backend/routes/agent_listeners_handlers_routes.py'),
    
    # Advanced Calculator
    ('backend/services/advanced_intelligent_calculator.py', '/var/www/html/vidgenerator/backend/services/advanced_intelligent_calculator.py'),
    ('backend/services/point_repair_restoration_system.py', '/var/www/html/vidgenerator/backend/services/point_repair_restoration_system.py'),
    ('backend/routes/advanced_calculator_routes.py', '/var/www/html/vidgenerator/backend/routes/advanced_calculator_routes.py'),
    ('vidgenerator/advanced_calculator/index.html', '/var/www/html/vidgenerator/vidgenerator/advanced_calculator/index.html'),
    
    # Updated register_blueprints
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
]

print("[1] Deploying files...")
for local_path, remote_path in files_to_deploy:
    try:
        if os.path.exists(local_path):
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create directory if needed
            remote_dir = os.path.dirname(remote_path)
            stdin, stdout, stderr = ssh.exec_command(f"mkdir -p {remote_dir}")
            stdout.read()
            
            # Write file
            with sftp.file(remote_path, 'w') as rf:
                rf.write(content)
            
            print(f"  [OK] Deployed: {local_path}")
        else:
            print(f"  [SKIP] File not found: {local_path}")
    except Exception as e:
        print(f"  [ERROR] Error deploying {local_path}: {e}")

sftp.close()

# Restart services
print("\n[2] Restarting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi && sleep 2 && systemctl restart apache2")
print("  [OK] Services restarted")

ssh.close()

print("\n" + "=" * 80)
print("DEPLOYMENT COMPLETE")
print("=" * 80)

