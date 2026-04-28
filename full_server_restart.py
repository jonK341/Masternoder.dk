"""
Full server restart - comprehensive service restart and cache clearing
"""
import paramiko
import os
import time

SERVER_HOST = os.getenv('DEPLOY_HOST', 'masternoder.dk')
USERNAME = os.getenv('DEPLOY_USER', 'root')
PASSWORD = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

if not PASSWORD:
    print("ERROR: DEPLOY_PASS environment variable not set!")
    exit(1)

print("=" * 80)
print("FULL SERVER RESTART - Comprehensive")
print("=" * 80)
print(f"Server: {SERVER_HOST}")
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # Step 1: Stop all Python/Flask processes
    print("[STEP 1] Stopping all Python/Flask processes...")
    commands = [
        "systemctl stop python-proxy.service 2>/dev/null || true",
        "systemctl stop uwsgi 2>/dev/null || true",
        "pkill -f 'python.*app.py' 2>/dev/null || true",
        "pkill -f 'flask' 2>/dev/null || true",
        "pkill -f 'uwsgi' 2>/dev/null || true",
    ]
    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()
        stderr.read()
    time.sleep(2)
    print("[OK] All processes stopped")
    print()

    # Step 2: Clear all caches
    print("[STEP 2] Clearing all caches...")
    cache_commands = [
        "find /var/www/html/vidgenerator -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true",
        "find /var/www/html/vidgenerator -type f -name '*.pyc' -delete 2>/dev/null || true",
        "find /var/www/html/vidgenerator -type f -name '*.pyo' -delete 2>/dev/null || true",
        "rm -rf /tmp/*.pyc 2>/dev/null || true",
        "sync",
    ]
    for cmd in cache_commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        stdout.read()
        stderr.read()
    print("[OK] All caches cleared")
    print()

    # Step 3: Verify files exist
    print("[STEP 3] Verifying critical files...")
    verify_files = [
        "/var/www/html/vidgenerator/backend/routes/game.py",
        "/var/www/html/vidgenerator/vidgenerator/battle/index.html",
        "/var/www/html/vidgenerator/vidgenerator/social/index.html",
        "/var/www/html/vidgenerator/vidgenerator/shop/index.html",
        "/var/www/html/vidgenerator/backend/services/daily_challenges.py",
        "/var/www/html/vidgenerator/backend/services/battle_system.py",
    ]
    for file_path in verify_files:
        stdin, stdout, stderr = ssh.exec_command(f"test -f {file_path} && echo 'EXISTS' || echo 'MISSING'")
        result = stdout.read().decode('utf-8').strip()
        status = "[OK]" if "EXISTS" in result else "[MISSING]"
        print(f"{status} {file_path}")
    print()

    # Step 4: Check Python syntax
    print("[STEP 4] Checking Python syntax...")
    syntax_check = "python3 -m py_compile /var/www/html/vidgenerator/backend/routes/game.py 2>&1"
    stdin, stdout, stderr = ssh.exec_command(syntax_check)
    output = stdout.read().decode('utf-8')
    errors = stderr.read().decode('utf-8')
    if errors and "SyntaxError" in errors:
        print(f"[ERROR] Syntax error: {errors}")
    else:
        print("[OK] No syntax errors")
    print()

    # Step 5: Restart services
    print("[STEP 5] Restarting services...")
    
    # Restart Flask
    print("  Restarting Flask Application...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart python-proxy.service")
    time.sleep(3)
    stdin, stdout, stderr = ssh.exec_command("systemctl status python-proxy.service --no-pager | grep -q 'active (running)' && echo 'ACTIVE' || echo 'INACTIVE'")
    flask_status = stdout.read().decode('utf-8').strip()
    if "ACTIVE" in flask_status:
        print("  [OK] Flask Application is active")
    else:
        print("  [WARNING] Flask Application status unclear")
    
    # Restart uWSGI
    print("  Restarting uWSGI...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart uwsgi")
    time.sleep(2)
    stdin, stdout, stderr = ssh.exec_command("systemctl status uwsgi --no-pager | grep -q 'active (running)' && echo 'ACTIVE' || echo 'INACTIVE'")
    uwsgi_status = stdout.read().decode('utf-8').strip()
    if "ACTIVE" in uwsgi_status:
        print("  [OK] uWSGI is active")
    else:
        print("  [WARNING] uWSGI status unclear")
    
    # Restart Nginx
    print("  Restarting Nginx...")
    stdin, stdout, stderr = ssh.exec_command("systemctl restart nginx")
    time.sleep(2)
    stdin, stdout, stderr = ssh.exec_command("systemctl status nginx --no-pager | grep -q 'active (running)' && echo 'ACTIVE' || echo 'INACTIVE'")
    nginx_status = stdout.read().decode('utf-8').strip()
    if "ACTIVE" in nginx_status:
        print("  [OK] Nginx is active")
    else:
        print("  [WARNING] Nginx status unclear")
    
    print()
    
    # Step 6: Wait for services to fully start
    print("[STEP 6] Waiting for services to stabilize...")
    time.sleep(5)
    print("[OK] Services should be ready")
    print()

    # Step 7: Check service status
    print("[STEP 7] Final service status check...")
    status_commands = [
        ("Flask", "systemctl is-active python-proxy.service"),
        ("uWSGI", "systemctl is-active uwsgi"),
        ("Nginx", "systemctl is-active nginx"),
    ]
    for name, cmd in status_commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        status = stdout.read().decode('utf-8').strip()
        marker = "[OK]" if status == "active" else "[WARNING]"
        print(f"{marker} {name}: {status}")
    print()

    print("=" * 80)
    print("[OK] Full server restart completed!")
    print("=" * 80)
    print()
    print("Next: Test URLs to verify routes are working")

    ssh.close()

except paramiko.AuthenticationException:
    print("[ERROR] Authentication failed. Check credentials.")
except Exception as e:
    print(f"[ERROR] {str(e)}")

