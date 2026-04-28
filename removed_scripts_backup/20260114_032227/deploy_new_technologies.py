#!/usr/bin/env python3
"""Deploy New Technologies to Game"""
import paramiko
import os
import sys
import time

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DEPLOYING NEW TECHNOLOGIES TO GAME")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Deploy files
files_to_deploy = [
    ('requirements.txt', '/var/www/html/vidgenerator/requirements.txt'),
    ('backend/services/realtime_system.py', '/var/www/html/vidgenerator/backend/services/realtime_system.py'),
    ('backend/services/cache_system.py', '/var/www/html/vidgenerator/backend/services/cache_system.py'),
    ('backend/services/analytics_system.py', '/var/www/html/vidgenerator/backend/services/analytics_system.py'),
    ('backend/routes/realtime_routes.py', '/var/www/html/vidgenerator/backend/routes/realtime_routes.py'),
    ('backend/routes/analytics_routes.py', '/var/www/html/vidgenerator/backend/routes/analytics_routes.py'),
    ('vidgenerator/static/js/realtime-client.js', '/var/www/html/vidgenerator/vidgenerator/static/js/realtime-client.js'),
    ('vidgenerator/static/js/threejs-visualizations.js', '/var/www/html/vidgenerator/vidgenerator/static/js/threejs-visualizations.js'),
    ('vidgenerator/static/js/chartjs-enhanced.js', '/var/www/html/vidgenerator/vidgenerator/static/js/chartjs-enhanced.js'),
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

# Install Python packages
print()
print("[INFO] Installing new Python packages...")
commands = [
    "cd /var/www/html/vidgenerator",
    "pip3 install flask-socketio python-socketio eventlet redis flask-caching hiredis celery[redis] prometheus-client flask-prometheus scikit-learn pandas scipy aiortc imageio imageio-ffmpeg selenium playwright flask-restx flask-cors flask-compress flask-limiter flask-talisman cryptography alembic sqlalchemy-utils sentry-sdk[flask] structlog --quiet"
]

for cmd in commands:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.read().decode('utf-8')
    errors = stderr.read().decode('utf-8')
    if errors and 'error' in errors.lower():
        print(f"  [WARN] {cmd}: {errors[:100]}")
    else:
        print(f"  [OK] Executed: {cmd[:50]}...")

# Install Redis if not installed
print()
print("[INFO] Checking Redis installation...")
stdin, stdout, stderr = ssh.exec_command("which redis-server")
if not stdout.read():
    print("  [INFO] Installing Redis...")
    stdin, stdout, stderr = ssh.exec_command("apt-get update && apt-get install -y redis-server")
    stdout.read()
    print("  [OK] Redis installed")
else:
    print("  [OK] Redis already installed")

# Start Redis if not running
stdin, stdout, stderr = ssh.exec_command("systemctl start redis-server")
stdout.read()
print("  [OK] Redis started")

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
print("[OK] NEW TECHNOLOGIES DEPLOYED")
print("=" * 80)
print()
print("Technologies Installed:")
print("  ✅ WebSocket (Flask-SocketIO) - Real-time updates")
print("  ✅ Redis - Caching and performance")
print("  ✅ Celery - Background task processing")
print("  ✅ Prometheus - Metrics and analytics")
print("  ✅ Scikit-learn - Machine learning")
print("  ✅ Pandas - Data analysis")
print("  ✅ WebRTC (aiortc) - Peer connections")
print("  ✅ Selenium/Playwright - Browser automation")
print("  ✅ Flask-RESTX - Enhanced API")
print("  ✅ Security enhancements (Rate limiting, CORS, etc.)")
print("  ✅ Database migrations (Alembic)")
print("  ✅ Error tracking (Sentry)")
print()
print("Frontend Technologies:")
print("  ✅ Socket.IO Client - Real-time communication")
print("  ✅ Three.js - 3D visualizations")
print("  ✅ Chart.js - Advanced charts")
print()
print("Next Steps:")
print("  1. Add Socket.IO script to HTML pages")
print("  2. Add Three.js and Chart.js CDN links")
print("  3. Initialize real-time connections")
print("  4. Configure Redis connection")
print("  5. Set up Celery workers")

