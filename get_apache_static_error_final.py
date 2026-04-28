"""
Get the exact Apache error when serving static files
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
print("GETTING EXACT APACHE ERROR FOR STATIC FILES")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # Trigger error
    print("[1] Triggering static file request...")
    trigger = "curl -s https://masternoder.dk/vidgenerator/static/css/modern-design-system.css > /dev/null 2>&1"
    ssh.exec_command(trigger)
    time.sleep(2)
    
    # Get latest errors
    print("[2] Getting latest Apache errors...")
    stdin, stdout, stderr = ssh.exec_command("tail -100 /var/log/apache2/error.log | grep -A 15 -B 5 'static\\|500\\|error.*css\\|Alias' | tail -50")
    errors = stdout.read().decode('utf-8', errors='ignore')
    if errors.strip():
        print("Apache errors:")
        print(errors)
    else:
        print("No specific errors found, showing all recent errors:")
        stdin, stdout, stderr = ssh.exec_command("tail -50 /var/log/apache2/error.log")
        print(stdout.read().decode('utf-8', errors='ignore'))
    print()

    # Check access log
    print("[3] Checking access log...")
    stdin, stdout, stderr = ssh.exec_command("tail -10 /var/log/apache2/access.log | grep 'static'")
    access = stdout.read().decode('utf-8', errors='ignore')
    if access.strip():
        print("Access log entries:")
        print(access)
    print()

    # Test Alias directly
    print("[4] Testing Alias path directly...")
    test_cmd = "curl -s -I http://127.0.0.1/vidgenerator/static/css/modern-design-system.css 2>&1 | head -15"
    stdin, stdout, stderr = ssh.exec_command(test_cmd)
    alias_test = stdout.read().decode('utf-8', errors='ignore')
    print("Alias test:")
    print(alias_test)
    print()

    # Check if mod_alias is enabled
    print("[5] Checking Apache modules...")
    stdin, stdout, stderr = ssh.exec_command("apache2ctl -M 2>&1 | grep -E 'alias|dir|expires|headers'")
    modules = stdout.read().decode('utf-8', errors='ignore')
    print("Required modules:")
    print(modules if modules.strip() else "Some modules might be missing")
    print()

    print("=" * 80)
    print("[OK] Error check complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

