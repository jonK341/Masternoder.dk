"""Check video for audio streams and file size."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VID_ID = "f5235d5b-9524-4a68-a7e5-a4ae4bb2786b"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4",
    f"ffprobe -v quiet -show_streams /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep -E 'codec_type|codec_name|sample_rate|channels|duration|width|height|bit_rate'",
    f"ffprobe -v quiet -show_format /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep -E 'nb_streams|duration|bit_rate'",
    f"find /var/www/html/vidgenerator/videos/ -name 'tts_*' -mmin -10 -ls 2>/dev/null",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode(errors='replace').strip()
    if out:
        print(out)

import os
ssh.close()
