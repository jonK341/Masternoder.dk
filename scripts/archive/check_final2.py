"""Check final video with audio."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VID_ID = "fcfe9a8e-507a-44da-ab80-b3d5a3dfb764"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password='eD)2[K+[S#m_#$3!', timeout=10)

cmds = [
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.audio_diag.json 2>/dev/null || echo 'NO DIAG'",
    f"ffprobe -v quiet -show_streams /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep -E 'codec_type|codec_name|sample_rate|channels|duration'",
    f"ffprobe -v quiet -show_format /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep -E 'nb_streams|duration|bit_rate'",
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:80]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode(errors='replace').strip())

ssh.close()
