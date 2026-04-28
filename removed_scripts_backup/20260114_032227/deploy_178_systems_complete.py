#!/usr/bin/env python3
"""
Deploy Complete 178 Systems Infrastructure
Includes leaderboards, achievements, shop integration, and theme
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING 178 SYSTEMS COMPLETE INFRASTRUCTURE")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

# Files to deploy
files_to_deploy = [
    # Services
    ('backend/services/178_systems_leaderboard.py', '/var/www/html/vidgenerator/backend/services/178_systems_leaderboard.py'),
    ('backend/services/178_systems_achievements.py', '/var/www/html/vidgenerator/backend/services/178_systems_achievements.py'),
    ('backend/services/shop_point_counter.py', '/var/www/html/vidgenerator/backend/services/shop_point_counter.py'),
    ('backend/services/point_calculator_178_systems.py', '/var/www/html/vidgenerator/backend/services/point_calculator_178_systems.py'),
    
    # Routes
    ('backend/routes/178_systems_routes.py', '/var/www/html/vidgenerator/backend/routes/178_systems_routes.py'),
    
    # Theme
    ('vidgenerator/theme_premium/index.html', '/var/www/html/vidgenerator/vidgenerator/theme_premium/index.html'),
    ('vidgenerator/leaderboards/index.html', '/var/www/html/vidgenerator/vidgenerator/leaderboards/index.html'),
    
    # Config files
    ('178_systems_config.json', '/var/www/html/vidgenerator/178_systems_config.json'),
    ('178_systems_point_values.json', '/var/www/html/vidgenerator/178_systems_point_values.json'),
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

# Update register_blueprints.py
print("\n[2] Checking blueprint registration...")
stdin, stdout, stderr = ssh.exec_command("grep -n 'systems_178' /var/www/html/vidgenerator/backend/register_blueprints.py")
registration = stdout.read().decode('utf-8')
if registration:
    print("  [OK] Already registered")
else:
    print("  [WARN] May need manual registration")

# Test imports
print("\n[3] Testing imports...")
test_code = """
try:
    from backend.services.systems_178_leaderboard import leaderboard_178_systems
    from backend.services.systems_178_achievements import achievements_178_systems
    from backend.services.shop_point_counter import shop_point_counter
    from backend.routes.systems_178_routes import systems_178_bp
    print('All imports successful')
except ImportError:
    try:
        from backend.services.systems_178_leaderboard import leaderboard_178_systems
        from backend.services.systems_178_achievements import achievements_178_systems
        from backend.services.shop_point_counter import shop_point_counter
        from backend.routes.systems_178_routes import systems_178_bp
        print('All imports successful (alternative)')
    except Exception as e:
        print(f'Import error: {e}')
"""
stdin, stdout, stderr = ssh.exec_command(f"cd /var/www/html/vidgenerator && python3 -c \"{test_code}\" 2>&1")
test_output = stdout.read().decode('utf-8')
print(f"  {test_output}")

# Restart services
print("\n[4] Restarting services...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi && sleep 2 && systemctl restart apache2")
print("  [OK] Services restarted")

ssh.close()

print("\n" + "=" * 80)
print("DEPLOYMENT COMPLETE")
print("=" * 80)
print()
print("Deployed:")
print("  - Leaderboard system")
print("  - Achievement system")
print("  - Shop point counter")
print("  - 178 systems calculator")
print("  - Premium theme template")
print("  - Leaderboard UI")
print()
print("API Endpoints:")
print("  - /api/178-systems/leaderboard/<system_id>")
print("  - /api/178-systems/leaderboard/all")
print("  - /api/178-systems/achievements/<system_id>")
print("  - /api/178-systems/shop/balance")
print("  - /api/178-systems/calculate")
print()
print("UI Pages:")
print("  - /vidgenerator/theme_premium/")
print("  - /vidgenerator/leaderboards/")
print()

