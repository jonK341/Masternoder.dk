"""Check Stability AI images and what's in the video."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    "find /var/www/html/vidgenerator/videos/ -name 'stability_*' -mmin -15 -ls 2>/dev/null",
    "ls -la /var/www/html/vidgenerator/videos/de484c8f-588e-465a-9e8e-126994cba16c.mp4",
    "python3 -c \"import json; d=json.load(open('/var/www/html/vidgenerator/videos/de484c8f-588e-465a-9e8e-126994cba16c.pipeline.json')); segs=d.get('rearranged_segments',[]); print('img paths:', [s.get('image_path') for s in segs])\"",
    # Check uWSGI app log for image generation details
    "find /var/www/html/logs/ -name '*.log' -mmin -15 2>/dev/null | head -10",
    "find /var/log/ -name '*uwsgi*' -o -name '*flask*' 2>/dev/null | head -10",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    if out:
        print(out[:2000])
    if err:
        print(f"ERR: {err[:500]}")

import os
ssh.close()
