"""Check video file info on production."""
import paramiko
import os

SERVER = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
VID_ID = "62bb82dc-74f5-4bff-aec5-a3c5b51e9a2c"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS, timeout=10)

cmds = [
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4",
    f"ffprobe -v error -show_format -show_streams /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | head -70",
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.audio_diag.json 2>/dev/null || echo 'no diag'",
]

for cmd in cmds:
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out.strip():
        print(out)
    if err.strip():
        print(err)
    print("---")

ssh.close()
