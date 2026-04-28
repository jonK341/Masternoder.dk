"""Read audio diagnostic."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

VID_ID = "2ac8ea0d-089d-4ee9-a724-326578b6f2b8"

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password='eD)2[K+[S#m_#$3!', timeout=10)

stdin, stdout, stderr = ssh.exec_command(
    f"cat /var/www/html/vidgenerator/videos/{VID_ID}.audio_diag.json 2>/dev/null || echo 'NO DIAG'"
)
print("DIAG:", stdout.read().decode(errors='replace'))

stdin, stdout, stderr = ssh.exec_command(
    f"ffprobe -v quiet -show_format /var/www/html/vidgenerator/videos/{VID_ID}.mp4 2>&1 | grep -E 'nb_streams|duration'"
)
print("FORMAT:", stdout.read().decode(errors='replace').strip())

stdin, stdout, stderr = ssh.exec_command(
    f"ls -lh /var/www/html/vidgenerator/videos/{VID_ID}.mp4"
)
print("SIZE:", stdout.read().decode(errors='replace').strip())

ssh.close()
