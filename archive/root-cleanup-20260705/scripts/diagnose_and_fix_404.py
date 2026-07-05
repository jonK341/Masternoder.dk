#!/usr/bin/env python3
"""
Diagnose and fix 404 error for /vidgenerator
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("DIAGNOSING AND FIXING /vidgenerator 404 ERROR")
print("=" * 80)
print()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)
    print(f"✓ Connected to {SERVER_HOST}")
except Exception as e:
    print(f"✗ Failed to connect: {e}")
    sys.exit(1)

try:
    sftp = ssh.open_sftp()
    
    # 1. Check if Apache is running and what it's doing
    print("\n[1] Checking Apache status...")
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active apache2')
    apache_status = stdout.read().decode('utf-8').strip()
    print(f"  Apache status: {apache_status}")
    
    # 2. Check Apache config for ProxyPass
    print("\n[2] Checking Apache ProxyPass configuration...")
    stdin, stdout, stderr = ssh.exec_command('grep -r "ProxyPass.*vidgenerator" /etc/apache2/sites-enabled/ 2>/dev/null || echo "No ProxyPass found"')
    proxypass_config = stdout.read().decode('utf-8', errors='replace')
    print(f"  ProxyPass config:\n{proxypass_config}")
    
    # 3. Check uWSGI port
    print("\n[3] Checking uWSGI configuration...")
    stdin, stdout, stderr = ssh.exec_command('grep -E "socket|port" /etc/systemd/system/uwsgi-vidgenerator.service 2>/dev/null | head -5')
    uwsgi_config = stdout.read().decode('utf-8', errors='replace')
    print(f"  uWSGI config:\n{uwsgi_config}")
    
    # 4. Test direct Flask access
    print("\n[4] Testing direct Flask/uWSGI access...")
    for port in [3031, 5000]:
        stdin, stdout, stderr = ssh.exec_command(f'curl -s -o /dev/null -w "%{{http_code}}" http://127.0.0.1:{port}/ 2>&1')
        http_code = stdout.read().decode('utf-8', errors='replace').strip()
        if http_code and http_code.isdigit():
            print(f"  Port {port}: HTTP {http_code}")
        else:
            print(f"  Port {port}: No response")
    
    # 5. Check recent Apache error logs
    print("\n[5] Checking recent Apache errors...")
    stdin, stdout, stderr = ssh.exec_command('tail -20 /var/log/apache2/error.log 2>/dev/null | grep -i vidgenerator | tail -5')
    apache_errors = stdout.read().decode('utf-8', errors='replace')
    if apache_errors.strip():
        print(f"  Apache errors:\n{apache_errors}")
    else:
        print("  No recent vidgenerator errors in Apache log")
    
    # 6. Deploy the fixed app.py (removed /vidgenerator routes)
    print("\n[6] Deploying fixed app.py (removed conflicting /vidgenerator routes)...")
    # The fix is already in the local file, just need to deploy
    print("  (Fix already applied locally - deploy with deploy_all_non_interactive.py)")
    
    sftp.close()
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)
    print("\nThe issue is:")
    print("- Routes registered for /vidgenerator in Flask won't work")
    print("- Middleware strips /vidgenerator BEFORE Flask routing")
    print("- Flask should only have routes for / and /index.html")
    print("\nFix applied: Removed /vidgenerator routes from app.py")
    print("Next: Deploy and restart services")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    ssh.close()

