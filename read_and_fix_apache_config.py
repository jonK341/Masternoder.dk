#!/usr/bin/env python3
"""
Read and properly fix Apache configuration
"""
import paramiko
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

SERVER_HOST = os.getenv("DEPLOY_HOST", "masternoder.dk")
USERNAME = os.getenv("DEPLOY_USER", "root")
PASSWORD = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=USERNAME, password=PASSWORD, timeout=60)

sftp = ssh.open_sftp()

# Read current config
with sftp.file('/etc/apache2/sites-enabled/000-default.conf', 'r') as f:
    config = f.read().decode('utf-8')

print("=" * 80)
print("CURRENT APACHE CONFIG (relevant parts):")
print("=" * 80)
lines = config.split('\n')
for i, line in enumerate(lines[25:70], 26):
    if 'vidgenerator' in line.lower() or 'proxypass' in line.lower() or '<location' in line.lower() or '</location' in line.lower():
        print(f"{i:3}: {line}")

# The key issue: We need ProxyPass /vidgenerator http://127.0.0.1:5000/vidgenerator
# NOT ProxyPass /vidgenerator http://127.0.0.1:5000/
# The prefix must be preserved so middleware can strip it

# Find and replace the ProxyPassMatch or ProxyPass that strips the prefix
print("\n" + "=" * 80)
print("FIXING CONFIGURATION...")
print("=" * 80)

# Remove ProxyPassMatch that strips prefix
config = config.replace('ProxyPassMatch ^/vidgenerator(.*)$ http://127.0.0.1:5000$1', '# ProxyPassMatch removed - was stripping prefix')

# Ensure we have the correct ProxyPass (preserving prefix)
if 'ProxyPass /vidgenerator http://127.0.0.1:5000/vidgenerator' not in config:
    # Add it before ProxyPassReverse
    config = config.replace(
        'ProxyPassReverse /vidgenerator',
        '    ProxyPass /vidgenerator http://127.0.0.1:5000/vidgenerator\n    ProxyPassReverse /vidgenerator'
    )

# Write fixed config
with sftp.file('/etc/apache2/sites-enabled/000-default.conf', 'w') as f:
    f.write(config.encode('utf-8'))

print("✓ Configuration fixed")
sftp.close()

# Test and restart
stdin, stdout, stderr = ssh.exec_command('apache2ctl configtest 2>&1')
test_result = stdout.read().decode('utf-8', errors='replace')
if 'Syntax OK' in test_result:
    print("✓ Syntax OK")
    ssh.exec_command('systemctl restart apache2')
    print("✓ Apache restarted")
else:
    print(f"✗ Syntax error: {test_result}")

ssh.close()
print("\n✓ Done")

