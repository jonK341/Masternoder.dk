"""Read audio diagnostic."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VID_ID = "ceba1a90-8b04-4589-93d5-6b51be220f3c"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.audio_diag.json 2>/dev/null || echo 'NO DIAG'"
)
print(stdout.read().decode(errors='replace'))

stdin, stdout, stderr = ssh.exec_command(
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4"
)
print(stdout.read().decode(errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command(
    f"ffprobe -v quiet -show_format /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep nb_streams"
)
print(stdout.read().decode(errors='replace').strip())

import os
ssh.close()
