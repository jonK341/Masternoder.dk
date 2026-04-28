#!/usr/bin/env python3
"""
Deploy All Undeployed Files
Checks for new files and deploys them, then restarts services
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING ALL UNDEPLOYED FILES")
print("=" * 80)
print()

# Files to deploy - comprehensive list
files_to_deploy = [
    # Encrypted JSON Storage
    ('backend/services/encrypted_json_storage.py', '/var/www/html/vidgenerator/backend/services/encrypted_json_storage.py'),
    
    # Behavior Pattern Monitor
    ('backend/services/behavior_pattern_monitor.py', '/var/www/html/vidgenerator/backend/services/behavior_pattern_monitor.py'),
    
    # Calculator Automation
    ('backend/services/calculator_automation.py', '/var/www/html/vidgenerator/backend/services/calculator_automation.py'),
    ('backend/routes/calculator_automation_routes.py', '/var/www/html/vidgenerator/backend/routes/calculator_automation_routes.py'),
    
    # Startup Automation
    ('backend/services/startup_automation.py', '/var/www/html/vidgenerator/backend/services/startup_automation.py'),
    
    # Master Control Dashboard
    ('vidgenerator/dashboard/master_control/index.html', '/var/www/html/vidgenerator/vidgenerator/dashboard/master_control/index.html'),
    
    # Agent Listeners/Handlers (if not already deployed)
    ('src/db/models_agent_listeners.py', '/var/www/html/vidgenerator/src/db/models_agent_listeners.py'),
    ('backend/services/agent_listeners_handlers_system.py', '/var/www/html/vidgenerator/backend/services/agent_listeners_handlers_system.py'),
    ('backend/routes/agent_listeners_handlers_routes.py', '/var/www/html/vidgenerator/backend/routes/agent_listeners_handlers_routes.py'),
    
    # Advanced Calculator (if not already deployed)
    ('backend/services/advanced_intelligent_calculator.py', '/var/www/html/vidgenerator/backend/services/advanced_intelligent_calculator.py'),
    ('backend/services/point_repair_restoration_system.py', '/var/www/html/vidgenerator/backend/services/point_repair_restoration_system.py'),
    ('backend/routes/advanced_calculator_routes.py', '/var/www/html/vidgenerator/backend/routes/advanced_calculator_routes.py'),
    ('vidgenerator/advanced_calculator/index.html', '/var/www/html/vidgenerator/vidgenerator/advanced_calculator/index.html'),
    
    # Updated app.py with startup automation
    ('src/app.py', '/var/www/html/vidgenerator/src/app.py'),
    
    # Updated register_blueprints
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
]

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"[1] Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    sftp = ssh.open_sftp()
    print("  [OK] Connected")
    print()
    
    print("[2] Deploying files...")
    deployed_count = 0
    skipped_count = 0
    error_count = 0
    
    for local_path, remote_path in files_to_deploy:
        try:
            if os.path.exists(local_path):
                # Read file
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
                deployed_count += 1
            else:
                print(f"  [SKIP] File not found: {local_path}")
                skipped_count += 1
        except Exception as e:
            print(f"  [ERROR] Error deploying {local_path}: {e}")
            error_count += 1
    
    sftp.close()
    print()
    print(f"Deployment Summary:")
    print(f"  Deployed: {deployed_count}")
    print(f"  Skipped: {skipped_count}")
    print(f"  Errors: {error_count}")
    print()
    
    # Restart services
    print("[3] Restarting uWSGI...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
    stdout.read()
    print("  [OK] uWSGI restarted")
    
    print("[4] Waiting 3 seconds...")
    import time
    time.sleep(3)
    
    print("[5] Restarting Apache...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart apache2")
    stdout.read()
    print("  [OK] Apache restarted")
    
    print()
    print("[6] Checking service status...")
    stdin, stdout, stderr = ssh.exec_command("systemctl is-active uwsgi && systemctl is-active apache2")
    status = stdout.read().decode('utf-8').strip()
    if 'active' in status:
        print("  [OK] Services are active")
    else:
        print(f"  [WARN] Service status: {status}")
    
    print()
    print("=" * 80)
    print("DEPLOYMENT COMPLETE - ALL SYSTEMS RESTARTED")
    print("=" * 80)
    print()
    print("Deployed files:")
    print(f"  - {deployed_count} files deployed successfully")
    print()
    print("Services restarted:")
    print("  - uWSGI (Flask application)")
    print("  - Apache (Web server)")
    print()
    print("Calculator automation will start automatically in 15 seconds!")
    print()
    
except Exception as e:
    print(f"[ERROR] Deployment failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
finally:
    try:
        ssh.close()
    except:
        pass

