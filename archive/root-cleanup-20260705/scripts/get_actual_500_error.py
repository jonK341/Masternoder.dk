"""
Get the actual 500 error from Apache logs
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
print("GETTING ACTUAL 500 ERROR FROM APACHE")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    print(f"Connecting to {SERVER_HOST}...")
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print("[OK] Connected!")
    print()

    # Clear error log marker
    print("[1] Triggering static file request to generate error...")
    trigger = "curl -s -I https://masternoder.dk/vidgenerator/static/css/modern-design-system.css 2>&1 | head -5"
    ssh.exec_command(trigger)
    time.sleep(2)
    
    # Get latest errors
    print("[2] Getting latest Apache errors...")
    stdin, stdout, stderr = ssh.exec_command("tail -100 /var/log/apache2/error.log | grep -A 20 -B 5 'static\\|500\\|error.*css' | tail -50")
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
    print("[3] Checking access log for static file request...")
    stdin, stdout, stderr = ssh.exec_command("tail -20 /var/log/apache2/access.log | grep 'static' | tail -5")
    access = stdout.read().decode('utf-8', errors='ignore')
    if access.strip():
        print("Access log entries:")
        print(access)
    print()

    # Test from server directly
    print("[4] Testing static file from server directly...")
    test_cmd = "curl -s -I http://127.0.0.1/vidgenerator/static/css/modern-design-system.css 2>&1 | head -10"
    stdin, stdout, stderr = ssh.exec_command(test_cmd)
    direct_test = stdout.read().decode('utf-8', errors='ignore')
    print("Direct server test:")
    print(direct_test)
    print()

    # Check current Apache config for ProxyPass
    print("[5] Checking ProxyPass configuration...")
    stdin, stdout, stderr = ssh.exec_command("grep -A 2 -B 2 'ProxyPass.*vidgenerator' /etc/apache2/sites-available/000-default.conf")
    proxypass_config = stdout.read().decode('utf-8', errors='ignore')
    if proxypass_config.strip():
        print("ProxyPass configuration:")
        print(proxypass_config)
    print()

    print("=" * 80)
    print("[OK] Error check complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

