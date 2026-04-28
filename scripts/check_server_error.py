"""Verify video integrity."""
import paramiko
import os

SERVER = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
VID = "62bb82dc-74f5-4bff-aec5-a3c5b51e9a2c"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER, username=USER, password=PASS, timeout=10)

cmds = [
    f"ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets /var/www/html/vidgenerator/videos/{VID}.mp4 2>&1",
    f"ffprobe -v error -show_entries format=duration,size,bit_rate /var/www/html/vidgenerator/videos/{VID}.mp4 2>&1",
    "journalctl -u uwsgi --since '5 min ago' --no-pager 2>/dev/null | tail -5",
    "dmesg -T 2>/dev/null | grep -i 'oom' | tail -3",
]

for i, cmd in enumerate(cmds):
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(f"--- {i+1} ---")
    print(stdout.read().decode().strip())

ssh.close()
