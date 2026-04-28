"""Check Flask app log."""
import paramiko

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password='eD)2[K+[S#m_#$3!', timeout=10)

stdin, stdout, stderr = ssh.exec_command("tail -200 /var/log/flask_app.log 2>/dev/null | tail -80")
out = stdout.read().decode(errors="replace").strip()
print(out[:4000])

ssh.close()
