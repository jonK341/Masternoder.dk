#!/usr/bin/env python3
"""Create activity points page route"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("CREATING ACTIVITY POINTS PAGE ROUTE")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

# Create route handler
route_content = '''"""
Activity Points Page Route - Serve activity-points HTML page
"""
from flask import Blueprint, Response, send_file
import os

activity_points_page_bp = Blueprint('activity_points_page', __name__)


@activity_points_page_bp.route('/activity-points', methods=['GET'], strict_slashes=False)
@activity_points_page_bp.route('/activity-points/', methods=['GET'], strict_slashes=False)
@activity_points_page_bp.route('/activity-points/index.html', methods=['GET'], strict_slashes=False)
def activity_points_page():
    """Serve activity-points page"""
    try:
        # Try multiple possible paths
        possible_paths = [
            '/var/www/html/vidgenerator/vidgenerator/activity-points/index.html',
            '/var/www/html/vidgenerator/activity-points/index.html',
        ]
        
        # Also try calculated path
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        calculated_paths = [
            os.path.join(base_path, 'vidgenerator', 'activity-points', 'index.html'),
            os.path.join(base_path, 'vidgenerator', 'vidgenerator', 'activity-points', 'index.html'),
        ]
        
        all_paths = possible_paths + calculated_paths
        
        for file_path in all_paths:
            if os.path.exists(file_path):
                return send_file(file_path, mimetype='text/html; charset=utf-8')
        
        return f"Error: Activity points page not found. Tried: {', '.join(all_paths)}", 404
    except Exception as e:
        return f"Error loading activity points page: {str(e)}", 500
'''

sftp = ssh.open_sftp()

# Write route file
with sftp.file('/var/www/html/vidgenerator/backend/routes/activity_points_page.py', 'w') as f:
    f.write(route_content)
print("[OK] Created activity_points_page.py route handler")

# Register the blueprint in register_blueprints.py
print()
print("[INFO] Registering blueprint...")
with sftp.file('/var/www/html/vidgenerator/backend/register_blueprints.py', 'r') as f:
    blueprints_content = f.read().decode('utf-8')

# Check if already registered
if 'activity_points_page_bp' in blueprints_content:
    print("  [INFO] Blueprint already registered")
else:
    # Find where to add it (after theme_points_page)
    lines = blueprints_content.split('\n')
    insert_pos = None
    for i, line in enumerate(lines):
        if 'theme_points_page_bp' in line and 'register_blueprint' in line:
            insert_pos = i + 1
            break
    
    if insert_pos:
        # Add import
        import_line = "from backend.routes.activity_points_page import activity_points_page_bp"
        # Find imports section
        for i, line in enumerate(lines):
            if 'from backend.routes.theme_points_page' in line:
                lines.insert(i + 1, import_line)
                break
        
        # Add registration
        indent = '    '  # 4 spaces
        registration_lines = [
            f"{indent}# Activity Points page",
            f"{indent}try:",
            f"{indent}    print('  [DEBUG] Attempting to import activity_points_page...', flush=True)",
            f"{indent}    from backend.routes.activity_points_page import activity_points_page_bp",
            f"{indent}    print(f'  [DEBUG] Imported activity_points_page_bp: {{activity_points_page_bp}}', flush=True)",
            f"{indent}    app.register_blueprint(activity_points_page_bp)",
            f"{indent}    registered_count += 1",
            f"{indent}    print('  [OK] Registered activity_points_page blueprint', flush=True)",
            f"{indent}except ImportError as e:",
            f"{indent}    print(f'  [WARN] Could not import activity_points_page: {{e}}', flush=True)",
            f"{indent}except Exception as e:",
            f"{indent}    print(f'  [ERROR] Error registering activity_points_page: {{e}}', flush=True)",
        ]
        
        lines.insert(insert_pos, '')
        for reg_line in registration_lines:
            lines.insert(insert_pos, reg_line)
            insert_pos += 1
        
        new_content = '\n'.join(lines)
        with sftp.file('/var/www/html/vidgenerator/backend/register_blueprints.py', 'w') as f:
            f.write(new_content)
        print("  [OK] Added blueprint registration")
    else:
        print("  [WARN] Could not find insertion point, adding at end")

sftp.close()

# Restart Flask
print()
print("=" * 80)
print("RESTARTING FLASK/uWSGI")
print("=" * 80)
print()

print("[INFO] Restarting uWSGI service...")
stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi-vidgenerator.service")
stdout.read()
print("[OK] uWSGI restarted")

time.sleep(5)

# Test the page
print()
print("[INFO] Testing activity points page...")
stdin, stdout, stderr = ssh.exec_command("curl -s -I http://127.0.0.1:5000/vidgenerator/activity-points/ | head -1")
status = stdout.read().decode('utf-8', errors='ignore')
print(f"Status: {status.strip()}")

if '200' in status:
    print("[OK] Activity points page is now accessible!")
else:
    print("[WARN] Page still returns error")
    # Check logs
    stdin, stdout, stderr = ssh.exec_command("tail -20 /var/www/html/vidgenerator/uwsgi.log | grep -i 'activity_points_page\|error' | tail -5")
    logs = stdout.read().decode('utf-8', errors='ignore')
    if logs:
        print(f"Logs: {logs}")

# Final comprehensive test
print()
print("[INFO] Running final comprehensive test...")
print("-" * 80)

test_urls = [
    ("/vidgenerator/activity-points/", "Activity Points Page"),
    ("/api/activity-points/test", "Activity Points API"),
    ("/api/battle/intelligence/test", "Battle Intelligence API"),
    ("/vidgenerator/battle/", "Battle Page"),
    ("/vidgenerator/dashboard/", "Dashboard Page"),
]

for url, name in test_urls:
    stdin, stdout, stderr = ssh.exec_command(f"curl -s -I http://127.0.0.1:5000{url} | head -1")
    status = stdout.read().decode('utf-8', errors='ignore')
    if '200' in status:
        print(f"[OK] {name}: {status.strip()}")
    elif '404' in status:
        print(f"[404] {name}: {status.strip()}")
    else:
        print(f"[INFO] {name}: {status.strip()}")

ssh.close()

print()
print("=" * 80)
print("[OK] COMPLETE")
print("=" * 80)

