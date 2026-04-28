"""Check server logs for video generation errors."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

cmds = [
    "tail -100 /var/log/uwsgi/vidgenerator.log 2>/dev/null | tail -60",
    "ls -la /var/www/html/backend/services/stability_image_service.py 2>/dev/null",
    "cd /var/www/html && python3 -c \"from backend.services.stability_image_service import is_available; print('Stability:', is_available())\" 2>&1",
    "cd /var/www/html && python3 -c \"from backend.services.llm_service import configured_providers; print('LLM:', configured_providers())\" 2>&1",
]

for cmd in cmds:
    print(f"\n>>> {cmd[:60]}...")
    stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode()
    err = stderr.read().decode()
    if out:
        print(out[-2000:])
    if err:
        print(f"STDERR: {err[-500:]}")

ssh.close()
