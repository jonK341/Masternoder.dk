"""Read diagnostic data from latest generation."""
import paramiko
import json
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VID_ID = "d3117c6c-6665-4b27-a170-a57c0a0fc545"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.diag.json 2>/dev/null || echo 'NO DIAG FILE'"
)
out = stdout.read().decode(errors='replace').strip()
print("Diagnostic:\n", out[:3000])

# Video file size
stdin, stdout, stderr = ssh.exec_command(
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4"
)
print(f"\nVideo: {stdout.read().decode().strip()}")

# Count new stability images
stdin, stdout, stderr = ssh.exec_command(
    "find /var/www/html/vidgenerator/videos/ -name 'stability_*' -mmin -10 -ls 2>/dev/null"
)
print(f"\nNew stability images:\n{stdout.read().decode().strip()}")

import os
ssh.close()
