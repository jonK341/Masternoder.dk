"""Install gTTS in the virtualenv as root."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    "/var/www/html/vidgenerator/.venv/bin/python3 -m pip install gTTS 2>&1 | tail -5",
    "/var/www/html/vidgenerator/.venv/bin/python3 -c 'from gtts import gTTS; print(\"gTTS OK\")'",
]

for cmd in cmds:
    print(f">>> {cmd[:70]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(5)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    if out:
        print(f"  {out}")
    if err and 'WARNING' not in err:
        print(f"  {err[:300]}")
    print()

import os
ssh.close()
