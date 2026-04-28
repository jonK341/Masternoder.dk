"""Check pipeline, add VIDEOS_DIR, verify AI content in the video."""
import paramiko
import json

VID_ID = "f556cf72-e306-4cc0-9ab5-21f0e120bf0e"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

# Find pipeline files anywhere
cmds = [
    "find /var/www/html -name 'pipeline_*' -mmin -15 2>/dev/null",
    f"ls -la /var/www/html/vidgenerator/videos/{VID_ID}* 2>/dev/null",
    f"find /var/www/html/vidgenerator/videos/ -name '{VID_ID}*' 2>/dev/null",
    "find /var/www/html/vidgenerator/videos/ -name 'pipeline_*' -mmin -15 2>/dev/null",
    "find /var/www/html -name '*.json' -mmin -15 -not -path '*/node_modules/*' 2>/dev/null | head -20",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    if out:
        print(out[:2000])
    else:
        print("  (empty)")

# Add VIDEOS_DIR to .env so images go to the same dir as videos
print("\n--- Adding VIDEOS_DIR to .env ---")
for ef in ["/var/www/html/.env", "/var/www/html/vidgenerator/.env"]:
    ssh.exec_command(f"sed -i '/^VIDEOS_DIR=/d' {ef}")
    import time; time.sleep(0.1)
    ssh.exec_command(f"echo 'VIDEOS_DIR=/var/www/html/vidgenerator/videos' >> {ef}")
    time.sleep(0.1)

stdin, stdout, stderr = ssh.exec_command("grep VIDEOS_DIR /var/www/html/.env")
print(stdout.read().decode().strip())

print("\n--- Restarting uWSGI ---")
ssh.exec_command("service uwsgi restart")
import time; time.sleep(3)
stdin, stdout, stderr = ssh.exec_command("ps aux | grep uwsgi | grep -v grep | wc -l")
print(f"Workers: {stdout.read().decode().strip()}")

import os
ssh.close()
print("\nDone.")
