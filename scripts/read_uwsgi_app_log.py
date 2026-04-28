"""Read the actual uWSGI app log."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

stdin, stdout, stderr = ssh.exec_command("grep -i 'VideoGen\\|Pre-render\\|image\\|stability\\|traceback\\|Error' /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | tail -50")
out = stdout.read().decode(errors='replace').strip()
print("Filtered log:\n", out[:5000] if out else "(empty)")

print("\n\n--- Last 40 lines ---")
stdin, stdout, stderr = ssh.exec_command("tail -40 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null")
out2 = stdout.read().decode(errors='replace').strip()
print(out2[:3000] if out2 else "(empty)")

import os
ssh.close()
