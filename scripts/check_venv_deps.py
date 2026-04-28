"""Check and install deps in the virtualenv."""
import paramiko
import time
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

VENV = "/var/www/html/vidgenerator/.venv/bin"

cmds = [
    f"{VENV}/python3 -c 'import moviepy; print(\"MoviePy:\", moviepy.__version__)'",
    f"{VENV}/pip install gTTS 2>&1 | tail -3",
    f"{VENV}/python3 -c 'from gtts import gTTS; print(\"gTTS OK\")'",
    f"{VENV}/python3 -c 'from moviepy.video.fx import FadeIn, FadeOut; print(\"FadeIn/FadeOut OK\")'",
    f"{VENV}/python3 -c 'from moviepy import VideoClip; print(\"VideoClip OK\")'",
    f"{VENV}/python3 -c 'import numpy; print(\"NumPy:\", numpy.__version__)'",
    f"{VENV}/python3 -c 'from PIL import Image; print(\"Pillow OK\")'",
]

for cmd in cmds:
    print(f">>> {cmd.split('/')[-1][:60]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(3)
    out = stdout.read().decode(errors='replace').strip()
    err = stderr.read().decode(errors='replace').strip()
    if out:
        print(f"  {out}")
    if err:
        print(f"  ERR: {err[:300]}")
    print()

import os
ssh.close()
