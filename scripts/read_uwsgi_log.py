"""Read uWSGI log for diagnostic output."""
import paramiko
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect("masternoder.dk", username="root", password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=10)

# Find uWSGI log location
cmds = [
    "find /var/log -name '*uwsgi*' -type f 2>/dev/null",
    "grep log-to /var/www/html/vidgenerator/uwsgi.ini 2>/dev/null || grep daemonize /var/www/html/vidgenerator/uwsgi.ini 2>/dev/null || cat /var/www/html/vidgenerator/uwsgi.ini 2>/dev/null | head -20",
]

for cmd in cmds:
    print(f">>> {cmd[:60]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    print(stdout.read().decode(errors='replace').strip())

# Read the right log
stdin, stdout, stderr = ssh.exec_command("cat /var/www/html/vidgenerator/uwsgi.ini")
ini = stdout.read().decode(errors='replace')
print(f"\nuwsgi.ini:\n{ini}")

# Look for our VideoGen log output
cmds2 = [
    "find /var/log -name '*.log' -newer /var/www/html/backend/services/llm_service.py 2>/dev/null",
    "grep -r 'VideoGen' /var/log/ 2>/dev/null | tail -20",
    "grep -r 'Pre-render' /var/log/ 2>/dev/null | tail -20",
]
for cmd in cmds2:
    print(f"\n>>> {cmd[:60]}")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode(errors='replace').strip()
    print(out[:2000] if out else "(empty)")

import os
ssh.close()
