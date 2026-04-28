"""Install gTTS on the server and check audio support."""
import paramiko
import time

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

cmds = [
    "pip3 install gTTS 2>&1 | tail -3",
    "python3 -c 'from gtts import gTTS; print(\"gTTS OK\")' 2>&1",
    "ffmpeg -codecs 2>/dev/null | grep -i aac | head -3",
    "ffmpeg -codecs 2>/dev/null | grep -i mp3 | head -3",
    "python3 -c 'import moviepy; print(\"MoviePy:\", moviepy.__version__)' 2>&1",
    "python3 -c 'from moviepy.video.fx import FadeIn, FadeOut; print(\"FadeIn/FadeOut OK\")' 2>&1",
    "python3 -c 'from moviepy import VideoClip; print(\"VideoClip OK\")' 2>&1",
]

for cmd in cmds:
    print(f">>> {cmd[:60]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    time.sleep(2)
    print(stdout.read().decode(errors='replace').strip())
    err = stderr.read().decode(errors='replace').strip()
    if err:
        print(f"  ERR: {err[:200]}")
    print()

import os
ssh.close()
