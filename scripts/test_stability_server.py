"""Upload and run a Stability AI test on the server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

test_script = """#!/usr/bin/env python3
import sys
sys.path.insert(0, '/var/www/html')
from backend.services.stability_image_service import is_available, generate_image, _get_api_key

print('Available:', is_available())
key = _get_api_key()
print('Key prefix:', key[:12] + '...' if key else 'NO KEY')

result = generate_image(
    prompt='A futuristic robot standing in a neon-lit city at night, cinematic, 4k',
    width=1024,
    height=576,
    steps=20,
    dest_dir='/var/www/html/vidgenerator/videos',
)
print('Result:', result)
"""

sftp = ssh.open_sftp()
with sftp.open("/tmp/test_stability.py", "w") as f:
    f.write(test_script)
sftp.close()

stdin, stdout, stderr = ssh.exec_command("cd /var/www/html && python3 /tmp/test_stability.py")
out = stdout.read().decode()
err = stderr.read().decode()
print("OUTPUT:", out)
if err:
    print("ERRORS:", err[-800:])

import os
ssh.close()
