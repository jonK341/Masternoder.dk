"""Check Flask app log for errors."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    "tail -100 /var/log/flask_app.log 2>/dev/null | grep -i 'stability\\|image\\|error\\|exception\\|traceback' | tail -30",
    "tail -200 /var/log/flask_app.log 2>/dev/null | tail -50",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode().strip()
    if out:
        print(out[:3000])
    else:
        print("  (empty)")

import os
ssh.close()
