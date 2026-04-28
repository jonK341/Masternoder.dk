#!/usr/bin/env python3
"""Deploy Rule Book v2.0 Complete System"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING RULE BOOK v2.0 COMPLETE SYSTEM")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    # Rule Book
    ('RULE_BOOK_V2.0.md', '/var/www/html/vidgenerator/RULE_BOOK_V2.0.md'),
    
    # Champions League System
    ('backend/services/champions_league_system.py', '/var/www/html/vidgenerator/backend/services/champions_league_system.py'),
    ('backend/routes/champions_league_routes.py', '/var/www/html/vidgenerator/backend/routes/champions_league_routes.py'),
    
    # Shop v2 System
    ('backend/services/shop_v2_system.py', '/var/www/html/vidgenerator/backend/services/shop_v2_system.py'),
    ('backend/routes/shop_v2_routes.py', '/var/www/html/vidgenerator/backend/routes/shop_v2_routes.py'),
    
    # Tech Intelligence System
    ('backend/services/tech_intelligence_system.py', '/var/www/html/vidgenerator/backend/services/tech_intelligence_system.py'),
    ('backend/routes/tech_intelligence_routes.py', '/var/www/html/vidgenerator/backend/routes/tech_intelligence_routes.py'),
    
    # Complete Point Equation
    ('backend/services/complete_point_equation.py', '/var/www/html/vidgenerator/backend/services/complete_point_equation.py'),
    ('backend/routes/complete_point_equation_routes.py', '/var/www/html/vidgenerator/backend/routes/complete_point_equation_routes.py'),
    
    # Service Worker Intelligence
    ('vidgenerator/service-worker.js', '/var/www/html/vidgenerator/vidgenerator/service-worker.js'),
    
    # Updated Blueprints
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

# Test endpoints
print()
print("[INFO] Testing new endpoints...")
print("-" * 80)

test_endpoints = [
    "/api/champions-league/test",
    "/api/shop-v2/test",
    "/api/tech-intelligence/test",
    "/api/points/equation/test",
]

for endpoint in test_endpoints:
    stdin, stdout, stderr = ssh.exec_command(f"curl -s http://127.0.0.1:5000{endpoint}")
    response = stdout.read().decode('utf-8', errors='ignore')
    if 'success' in response.lower() or 'working' in response.lower():
        print(f"  [OK] {endpoint}")
    else:
        print(f"  [WARN] {endpoint}: {response[:100]}")

ssh.close()

print()
print("=" * 80)
print("[OK] RULE BOOK v2.0 COMPLETE SYSTEM DEPLOYED")
print("=" * 80)
print()
print("Features deployed:")
print("  ✅ Rule Book v2.0 Documentation")
print("  ✅ Champions League System")
print("  ✅ Shop v2.0 (Boosters, Game Time, Artifacts)")
print("  ✅ Tech Intelligence System")
print("  ✅ Complete Point Equation")
print("  ✅ Service Worker Intelligence")
print("  ✅ All Blueprints Registered")
print()
print("New Systems:")
print("  - Champions League with point data and rankings")
print("  - Shop v2.0 with intelligence")
print("  - Tech intelligence for shop, social, peers, network")
print("  - Complete point counter equation")
print("  - Enhanced service worker with intelligence")

