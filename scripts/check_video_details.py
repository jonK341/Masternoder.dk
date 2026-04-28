"""Check video generation pipeline details on server."""
import paramiko
import json

VID_ID = "f556cf72-e306-4cc0-9ab5-21f0e120bf0e"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    f"cat /var/www/html/logs/video_status/{VID_ID}.json 2>/dev/null || echo 'NO SIDECAR'",
    f"ls -la /var/www/html/vidgenerator/output/{VID_ID}* 2>/dev/null || echo 'NO OUTPUT FILES'",
    f"find /var/www/html/vidgenerator/output/ -name '*{VID_ID}*' -o -name '*pipeline*' 2>/dev/null | head -10",
    f"find /var/www/html/logs/ -name '*{VID_ID}*' 2>/dev/null | head -10",
    f"find /var/www/html/ -name 'pipeline_{VID_ID}*' -o -name '{VID_ID}_pipeline*' 2>/dev/null | head -10",
    "find /var/www/html/logs/ -name 'pipeline_*.json' -newer /var/www/html/backend/services/llm_service.py 2>/dev/null | head -5",
    "find /var/www/html/vidgenerator/output/ -name '*.mp4' -newer /var/www/html/backend/services/llm_service.py 2>/dev/null | head -5",
    "find /var/www/html/ -name 'stability_*.png' 2>/dev/null | head -5",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    if out:
        print(out[:2000])
    else:
        print("  (empty)")

import os
ssh.close()
