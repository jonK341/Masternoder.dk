"""Find where video output goes on the server."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    "grep -r VIDEOS_DIR /var/www/html/.env 2>/dev/null",
    "grep -r OUTPUT_DIR /var/www/html/.env 2>/dev/null",
    "find /var/www/html -name '*.mp4' -mmin -10 2>/dev/null",
    "find /tmp -name '*.mp4' -mmin -10 2>/dev/null",
    "find /var/www -name '*.mp4' -mmin -10 2>/dev/null",
    "ls -la /var/www/html/logs/video_status/ 2>/dev/null || echo 'DIR MISSING'",
    "ls -la /var/www/html/vidgenerator/output/ 2>/dev/null | tail -10",
    "find /var/www/html -name 'pipeline_*.json' -mmin -10 2>/dev/null",
    "find /var/www/html -name '*.json' -path '*/video_status/*' 2>/dev/null | head -5",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    if out:
        print(out[:1000])
    else:
        print("  (empty)")

import os
ssh.close()
