"""
Get the real Apache error for static files
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
print("GETTING REAL APACHE ERROR FOR STATIC FILES")
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
    time.sleep(1)
    
    # Get latest errors
    print("[2] Getting latest Apache errors...")
    stdin, stdout, stderr = ssh.exec_command("tail -100 /var/log/apache2/error.log | grep -A 10 -B 5 'static\\|500\\|error' | tail -50")
    errors = stdout.read().decode('utf-8', errors='ignore')
    if errors.strip():
        print("Apache errors:")
        print(errors)
    else:
        print("No specific errors found, showing recent log entries:")
        stdin, stdout, stderr = ssh.exec_command("tail -30 /var/log/apache2/error.log")
        print(stdout.read().decode('utf-8', errors='ignore'))
    print()

    # Check if mod_headers is enabled
    print("[3] Checking Apache modules...")
    stdin, stdout, stderr = ssh.exec_command("apache2ctl -M 2>&1 | grep -E 'headers|alias|dir|expires'")
    modules = stdout.read().decode('utf-8', errors='ignore')
    print("Required modules:")
    print(modules if modules.strip() else "Some modules might be missing")
    print()

    # Test direct file access
    print("[4] Testing direct file access...")
    stdin, stdout, stderr = ssh.exec_command("sudo -u www-data cat /var/www/html/vidgenerator/vidgenerator/static/css/modern-design-system.css | head -5")
    file_content = stdout.read().decode('utf-8', errors='ignore')
    if file_content.strip():
        print("[OK] File is readable by www-data")
        print("First 5 lines:")
        print(file_content)
    else:
        print("[ERROR] File is not readable by www-data")
    print()

    # Check Apache config for LocationMatch
    print("[5] Checking LocationMatch in config...")
    stdin, stdout, stderr = ssh.exec_command("grep -n 'LocationMatch' /etc/apache2/sites-available/000-default.conf")
    locationmatch = stdout.read().decode('utf-8', errors='ignore')
    if locationmatch.strip():
        print("LocationMatch found:")
        print(locationmatch)
    print()

    print("=" * 80)
    print("[OK] Error check complete!")
    print("=" * 80)

    ssh.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()

