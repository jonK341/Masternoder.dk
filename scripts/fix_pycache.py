import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=30):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# Delete ALL .pyc files so Python uses the .py source
print("Clearing all .pyc / __pycache__ files...")
o, e = run("find /var/www/html/vidgenerator/backend -name '*.pyc' -delete && find /var/www/html/vidgenerator/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo DONE")
print(f"  {o}")

print("Restarting uWSGI (stop + start)...")
run("systemctl stop uwsgi", t=10)
time.sleep(2)
o, e = run("systemctl start uwsgi", t=10)
print(f"  start: {o or 'ok'}")
time.sleep(8)

# Test
o, _ = run("curl -s 'http://localhost:5000/api/system/overview?compact=1' --max-time 12 -w '\\nSTATUS:%{http_code}'")
print("Test result:", o[:500])

import os
ssh.close()
