import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=15):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

o, _ = run("grep -n 'system_overview' /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py | head -5")
print("missing_endpoints grep:", o or "(not found)")

o, _ = run("wc -l /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py")
print("missing_endpoints lines:", o)

o, _ = run("python3 -c 'import sys; sys.path.insert(0,\"/var/www/html\"); from backend.routes.missing_endpoints_routes import missing_endpoints_bp; print(\"OK import\")' 2>&1")
print("import test:", o)

# Check what routes are registered that match system
o, _ = run("journalctl -u uwsgi --since '2 min ago' | grep -i 'system_overview\\|overview\\|ERROR\\|error' | tail -20")
print("uwsgi log:", o or "(empty)")

import os
ssh.close()
