"""
Get actual Apache error when accessing static files
"""
import paramiko
import os
import sys
import time

# Configure UTF-8 for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv('DEPLOY_HOST', 'masternoder.dk')
USERNAME = os.getenv('DEPLOY_USER', 'root')
PASSWORD = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

print("=" * 80)
print("GETTING APACHE ERROR FOR STATIC FILES")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # Clear error log to see only new errors
    print("[1] Triggering static file request to generate error...")
    trigger_cmd = "curl -s https://masternoder.dk/vidgenerator/static/css/modern-design-system.css > /dev/null 2>&1 &"
    ssh.exec_command(trigger_cmd)
    time.sleep(2)
    
    # Get latest errors
    print("[2] Getting latest Apache errors...")
    log_cmd = "tail -50 /var/log/apache2/error.log | grep -A 5 -B 5 'static\\|vidgenerator/static\\|500' | tail -30"
    stdin, stdout, stderr = ssh.exec_command(log_cmd)
    errors = stdout.read().decode('utf-8', errors='ignore')
    
    if errors.strip():
        print("Apache errors:")
        print(errors)
    else:
        print("No recent errors found, checking all recent errors...")
        stdin, stdout, stderr = ssh.exec_command("tail -30 /var/log/apache2/error.log")
        all_errors = stdout.read().decode('utf-8', errors='ignore')
        print(all_errors)
    print()

    # Check access log
    print("[3] Checking access log for static file requests...")
    access_cmd = "tail -20 /var/log/apache2/access.log | grep 'static' | tail -5"
    stdin, stdout, stderr = ssh.exec_command(access_cmd)
    access = stdout.read().decode('utf-8', errors='ignore')
    if access.strip():
        print("Access log entries:")
        print(access)
    print()

    # Test file permissions
    print("[4] Checking file permissions...")
    perm_cmd = "ls -la /var/www/html/vidgenerator/vidgenerator/static/css/modern-design-system.css"
    stdin, stdout, stderr = ssh.exec_command(perm_cmd)
    perms = stdout.read().decode('utf-8', errors='ignore')
    print(f"File permissions: {perms.strip()}")
    
    # Check if Apache user can read the file
    apache_user_cmd = "sudo -u www-data test -r /var/www/html/vidgenerator/vidgenerator/static/css/modern-design-system.css && echo 'READABLE' || echo 'NOT READABLE'"
    stdin, stdout, stderr = ssh.exec_command(apache_user_cmd)
    readable = stdout.read().decode('utf-8', errors='ignore').strip()
    print(f"Apache user (www-data) can read: {readable}")
    print()

    # Check Apache modules
    print("[5] Checking required Apache modules...")
    modules_cmd = "apache2ctl -M 2>/dev/null | grep -E 'alias|dir|expires'"
    stdin, stdout, stderr = ssh.exec_command(modules_cmd)
    modules = stdout.read().decode('utf-8', errors='ignore')
    if modules.strip():
        print("Required modules loaded:")
        print(modules)
    else:
        print("[WARN] Some required modules might not be loaded")
    print()

    print("=" * 80)
    print("[OK] Error check complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

