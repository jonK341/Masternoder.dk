"""Check the final video with animations and audio."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VID_ID = "c0a5e507-09a2-4ad5-a653-eec54e6a16d7"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4",
    f"ffprobe -v quiet -show_format -show_streams /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep -E 'codec_name|duration|width|height|nb_streams|bit_rate|sample_rate|channels'",
    f"find /var/www/html/vidgenerator/videos/ -name 'picsum_*' -newer /var/www/html/vidgenerator/videos/{VID_ID}.pipeline.json -ls 2>/dev/null | head -5",
    f"find /var/www/html/vidgenerator/videos/ -name 'tts_*' -mmin -5 -ls 2>/dev/null",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    if out:
        print(out)
    if err:
        print(f"ERR: {err[:300]}")

import os
ssh.close()
