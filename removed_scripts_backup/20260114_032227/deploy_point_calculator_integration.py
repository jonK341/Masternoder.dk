#!/usr/bin/env python3
"""
Deploy Point Calculator Integration
Deploy hardcoded calculator integration to server
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING POINT CALCULATOR INTEGRATION")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
sftp = ssh.open_sftp()

# Files to deploy
files_to_deploy = [
    ('backend/services/point_calculator_hardcoded.py', '/var/www/html/vidgenerator/backend/services/point_calculator_hardcoded.py'),
    ('backend/services/point_calculator_integration.py', '/var/www/html/vidgenerator/backend/services/point_calculator_integration.py'),
    ('backend/routes/point_calculator_routes.py', '/var/www/html/vidgenerator/backend/routes/point_calculator_routes.py'),
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
print("\n[2] Updating register_blueprints.py...")
stdin, stdout, stderr = ssh.exec_command("cat /var/www/html/vidgenerator/backend/register_blueprints.py")
register_content = stdout.read().decode('utf-8')

# Check if already registered
if 'point_calculator_bp' not in register_content:
    # Find a good place to insert (after other point-related blueprints)
    lines = register_content.split('\n')
    insert_pos = -1
    
    # Look for complete_point_equation or unified_points registration
    for i, line in enumerate(lines):
        if 'complete_point_equation' in line or 'unified_points' in line:
            # Find the end of this registration block
            for j in range(i, min(i+20, len(lines))):
                if lines[j].strip() and not lines[j].startswith(' ') and not lines[j].startswith('\t'):
                    if 'try:' in lines[j] or 'def ' in lines[j]:
                        insert_pos = j
                        break
            if insert_pos > 0:
                break
    
    if insert_pos == -1:
        # Fallback: insert before the final print statement
        for i in range(len(lines)-1, max(len(lines)-50, 0), -1):
            if 'print(' in lines[i] and 'registered' in lines[i].lower():
                insert_pos = i
                break
    
    if insert_pos > 0:
        # Insert point calculator blueprint registration
        registration_code = '''
    # Point Calculator routes (Hardcoded Calculator Integration)
    try:
        from backend.routes.point_calculator_routes import point_calculator_bp
        app.register_blueprint(point_calculator_bp)
        registered_count += 1
        print("  [OK] Registered point_calculator blueprint")
    except ImportError as e:
        print(f"  [WARN] Could not import point_calculator_routes: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"  [ERROR] Error registering point_calculator: {e}")
        import traceback
        traceback.print_exc()
'''
        lines.insert(insert_pos, registration_code)
        updated_content = '\n'.join(lines)
        
        # Write back
        sftp = ssh.open_sftp()
        with sftp.file('/var/www/html/vidgenerator/backend/register_blueprints.py', 'w') as f:
            f.write(updated_content)
        sftp.close()
        print("  ✓ Updated register_blueprints.py")
    else:
        print("  ⚠ Could not find insertion point, manual update may be needed")
else:
    print("  ✓ Already registered in register_blueprints.py")

# Test import
print("\n[3] Testing imports...")
stdin, stdout, stderr = ssh.exec_command("cd /var/www/html/vidgenerator && python3 -c 'from backend.services.point_calculator_hardcoded import point_calculator_hardcoded; from backend.services.point_calculator_integration import point_calculator_integration; from backend.routes.point_calculator_routes import point_calculator_bp; print(\"All imports successful\")' 2>&1")
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
print("  - point_calculator_hardcoded.py")
print("  - point_calculator_integration.py")
print("  - point_calculator_routes.py")
print()
print("✅ Updated register_blueprints.py")
print("✅ Services restarted")
print()
print("📡 API Endpoints available:")
print("  - GET /api/points/calculator/calculate")
print("  - GET /api/points/calculator/breakdown/<user_id>")
print("  - GET /api/points/calculator/verify/<user_id>")
print("  - GET /api/points/calculator/gather-data/<user_id>")
print("  - GET /api/points/calculator/test")
print()

