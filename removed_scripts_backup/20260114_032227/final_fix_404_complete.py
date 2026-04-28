#!/usr/bin/env python3
"""
FINAL FIX - Complete 404 error resolution
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

print("=" * 80)
print("FINAL FIX - COMPLETE 404 RESOLUTION")
print("=" * 80)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# 1. Check if Flask is running
print("\n[1] Checking if Flask/uWSGI is running...")
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:5000/ 2>&1')
flask_status = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  Flask on port 5000: HTTP {flask_status}")

if flask_status == '000' or not flask_status.isdigit():
    print("  ✗ Flask is not responding on port 5000!")
    print("  Checking uWSGI service...")
    stdin, stdout, stderr = ssh.exec_command('systemctl is-active uwsgi-vidgenerator.service')
    uwsgi_active = stdout.read().decode('utf-8', errors='replace').strip()
    print(f"  uWSGI service status: {uwsgi_active}")
    
    if uwsgi_active != 'active':
        print("  ⚠️  uWSGI is not active - starting it...")
        ssh.exec_command('systemctl start uwsgi-vidgenerator.service')
        import time
        time.sleep(3)
        stdin, stdout, stderr = ssh.exec_command('systemctl is-active uwsgi-vidgenerator.service')
        uwsgi_active = stdout.read().decode('utf-8', errors='replace').strip()
        print(f"  uWSGI status after start: {uwsgi_active}")

# 2. Read and fix Apache config properly
print("\n[2] Reading and fixing Apache configuration...")
with sftp.file('/etc/apache2/sites-enabled/000-default.conf', 'r') as f:
    config = f.read().decode('utf-8')

# Find the VirtualHost section
# We need ONE clean ProxyPass configuration
# Remove all conflicting ProxyPass directives and create a clean one

lines = config.split('\n')
new_lines = []
in_vidgenerator_location = False
skip_until_end_location = False
added_proxypass = False

for i, line in enumerate(lines):
    # Skip old ProxyPass/ProxyPassReverse for vidgenerator outside Location blocks
    if 'ProxyPassReverse /vidgenerator' in line and not in_vidgenerator_location and 'ProxyPass /vidgenerator' not in lines[max(0, i-2):i]:
        # Skip orphaned ProxyPassReverse
        continue
    
    # Handle Location block
    if '<Location /vidgenerator>' in line or '<Location "/vidgenerator">' in line:
        in_vidgenerator_location = True
        new_lines.append('    <Location /vidgenerator>')
        new_lines.append('        ProxyPass http://127.0.0.1:5000/vidgenerator')
        new_lines.append('        ProxyPassReverse http://127.0.0.1:5000/vidgenerator')
        new_lines.append('        ProxyPreserveHost On')
        added_proxypass = True
        skip_until_end_location = True
        continue
    
    if skip_until_end_location:
        if '</Location>' in line:
            new_lines.append('    </Location>')
            skip_until_end_location = False
            in_vidgenerator_location = False
        # Skip lines inside Location block (we've already added what we need)
        continue
    
    new_lines.append(line)

# If we didn't add ProxyPass in Location block, add it after VirtualHost opening
if not added_proxypass:
    # Find VirtualHost opening and add after it
    for i, line in enumerate(new_lines):
        if '<VirtualHost' in line and 'ProxyPass /vidgenerator' not in '\n'.join(new_lines[i:i+50]):
            # Insert after VirtualHost tag (find next non-empty line)
            insert_pos = i + 1
            while insert_pos < len(new_lines) and new_lines[insert_pos].strip() == '':
                insert_pos += 1
            new_lines.insert(insert_pos, '    ProxyPass /vidgenerator http://127.0.0.1:5000/vidgenerator')
            new_lines.insert(insert_pos + 1, '    ProxyPassReverse /vidgenerator http://127.0.0.1:5000/vidgenerator')
            new_lines.insert(insert_pos + 2, '    ProxyPreserveHost On')
            break

new_config = '\n'.join(new_lines)

# Backup and write
with sftp.file('/etc/apache2/sites-enabled/000-default.conf.backup.final_fix', 'w') as f:
    f.write(config.encode('utf-8'))

with sftp.file('/etc/apache2/sites-enabled/000-default.conf', 'w') as f:
    f.write(new_config.encode('utf-8'))

print("  ✓ Apache config fixed")

# Test config
stdin, stdout, stderr = ssh.exec_command('apache2ctl configtest 2>&1')
test_result = stdout.read().decode('utf-8', errors='replace')
if 'Syntax OK' in test_result:
    print("  ✓ Config syntax OK")
    
    # Restart Apache
    ssh.exec_command('systemctl restart apache2')
    print("  ✓ Apache restarted")
else:
    print(f"  ✗ Config error: {test_result}")
    # Restore backup
    with sftp.file('/etc/apache2/sites-enabled/000-default.conf', 'w') as f:
        f.write(config.encode('utf-8'))
    print("  ⚠️  Restored backup")

sftp.close()

# Test the fix
print("\n[3] Testing the fix...")
stdin, stdout, stderr = ssh.exec_command('curl -s -o /dev/null -w "%{http_code}" http://localhost/vidgenerator 2>&1')
apache_response = stdout.read().decode('utf-8', errors='replace').strip()
print(f"  Apache proxy response: HTTP {apache_response}")

if apache_response == '200':
    print("\n" + "=" * 80)
    print("✅ SUCCESS! /vidgenerator now returns 200")
    print("=" * 80)
elif apache_response == '404':
    print("\n" + "=" * 80)
    print("⚠️  Still 404 - Flask may not be running or route not matching")
    print("=" * 80)
    print("\nCheck:")
    print("  1. systemctl status uwsgi-vidgenerator.service")
    print("  2. journalctl -u uwsgi-vidgenerator.service -n 50")
    print("  3. curl http://127.0.0.1:5000/")
else:
    print(f"\n  Response: HTTP {apache_response}")

ssh.close()
print("\n✓ Done")

