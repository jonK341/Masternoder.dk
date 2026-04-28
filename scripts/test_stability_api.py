"""Test Stability AI API directly on the server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

test_code = '''
import sys
sys.path.insert(0, "/var/www/html")
from backend.services.stability_image_service import is_available, generate_image, _get_api_key

print("Available:", is_available())
key = _get_api_key()
print("Key prefix:", key[:12] + "..." if key else "NO KEY")

result = generate_image(
    prompt="A futuristic robot standing in a neon-lit city at night, cinematic, 4k",
    width=1024,
    height=576,
    steps=20,
    dest_dir="/var/www/html/vidgenerator/videos",
)
print("Result:", result)
'''

stdin, stdout, stderr = ssh.exec_command(f'cd /var/www/html && python3 -c "{test_code}"')
out = stdout.read().decode()
err = stderr.read().decode()
print("STDOUT:", out)
if err:
    print("STDERR:", err[-500:])

import os
ssh.close()
