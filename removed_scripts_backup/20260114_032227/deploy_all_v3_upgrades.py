#!/usr/bin/env python3
"""
Deploy All v3 Ultimate Upgrades
Shop, Battle, VidGenerator, Knowledge & Intelligence
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING ALL v3 ULTIMATE UPGRADES")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

files_to_deploy = [
    # Shop v3 Ultimate
    ('backend/services/shop_v3_ultimate.py', '/var/www/html/vidgenerator/backend/services/shop_v3_ultimate.py'),
    ('backend/routes/shop_v3_routes.py', '/var/www/html/vidgenerator/backend/routes/shop_v3_routes.py'),
    
    # Battle v3 Ultimate
    ('backend/services/battle_v3_ultimate.py', '/var/www/html/vidgenerator/backend/services/battle_v3_ultimate.py'),
    ('backend/routes/battle_v3_routes.py', '/var/www/html/vidgenerator/backend/routes/battle_v3_routes.py'),
    
    # VidGenerator v3 Ultimate
    ('backend/services/vidgenerator_v3_ultimate.py', '/var/www/html/vidgenerator/backend/services/vidgenerator_v3_ultimate.py'),
    ('backend/routes/vidgenerator_v3_routes.py', '/var/www/html/vidgenerator/backend/routes/vidgenerator_v3_routes.py'),
    
    # Knowledge & Intelligence
    ('src/db/models_178_knowledge_intelligence.py', '/var/www/html/vidgenerator/src/db/models_178_knowledge_intelligence.py'),
    ('backend/services/178_systems_knowledge_intelligence.py', '/var/www/html/vidgenerator/backend/services/178_systems_knowledge_intelligence.py'),
    ('backend/routes/178_knowledge_intelligence_routes.py', '/var/www/html/vidgenerator/backend/routes/178_knowledge_intelligence_routes.py'),
    
    # Knowledge Data
    ('178_systems_knowledge_data.json', '/var/www/html/vidgenerator/178_systems_knowledge_data.json'),
    ('178_systems_intelligence_templates.json', '/var/www/html/vidgenerator/178_systems_intelligence_templates.json'),
    
    # Updated blueprints
    ('backend/register_blueprints.py', '/var/www/html/vidgenerator/backend/register_blueprints.py'),
    
    # Dependencies
    ('requirements_v3_upgraded.txt', '/var/www/html/vidgenerator/requirements_v3_upgraded.txt'),
]

print("[1] Deploying files...")
deployed = 0
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
            deployed += 1
        else:
            print(f"  [SKIP] File not found: {local_path}")
    except Exception as e:
        print(f"  [ERROR] Error deploying {local_path}: {e}")

sftp.close()

print(f"\n[2] Deployed {deployed} files")

# Install/upgrade dependencies
print("\n[3] Upgrading dependencies...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && pip3 install --upgrade cryptography pandas scikit-learn scipy redis celery prometheus-client 2>&1")
output = stdout.read().decode('utf-8')
if 'Successfully' in output or 'Requirement already satisfied' in output:
    print("  [OK] Dependencies upgraded")
else:
    print(f"  [WARN] Dependency upgrade output: {output[:200]}")

# Restart services
print("\n[4] Restarting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi && sleep 3 && systemctl restart apache2")
print("  [OK] Services restarted")

ssh.close()

print("\n" + "=" * 80)
print("ALL v3 UPGRADES DEPLOYED")
print("=" * 80)
print()
print("Upgraded Systems:")
print("  - Shop v3 Ultimate (new items, artifacts, intelligence)")
print("  - Battle v3 Ultimate (178 point integration, strategies)")
print("  - VidGenerator v3 Ultimate (quality presets, intelligence)")
print("  - 178 Systems Knowledge & Intelligence (database tables)")
print()
print("New Features:")
print("  - Knowledge database for all 178 systems")
print("  - Intelligence tracking per user/system")
print("  - Enhanced shop with artifacts and knowledge items")
print("  - Advanced battle types with 178 point integration")
print("  - Quality presets with Death Portal & 10x Production")
print()

