"""Check what's happening with the generation on the server."""
import paramiko

VID_ID = "77546293-9770-442c-b49b-a10433e134f1"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    f"cat /var/www/html/logs/video_status/{VID_ID}.json 2>/dev/null || echo 'NO SIDECAR FILE'",
    f"ls -la /var/www/html/logs/video_status/ 2>/dev/null | tail -5",
    "ps aux | grep -i uwsgi | head -5",
    "ps aux | grep -i flask | head -3",
    "tail -30 /var/log/uwsgi/vidgenerator.log 2>/dev/null || echo 'no uwsgi log'",
    "tail -30 /var/log/flask/*.log 2>/dev/null || echo 'no flask log'",
    "journalctl -u uwsgi --no-pager -n 20 2>/dev/null || journalctl -u flask-app --no-pager -n 20 2>/dev/null || echo 'no journal'",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:70]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out[-1000:])
    if err:
        print(f"STDERR: {err[-300:]}")

import os
ssh.close()
