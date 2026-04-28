import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()

# How many uwsgi services are there?
o, _ = run("systemctl list-units --type=service | grep -i uwsgi")
print("All uwsgi services:")
print(o)
print()

# Find all uwsgi processes and their ini files
o, _ = run("ps aux | grep uwsgi | grep -v grep | head -20")
print("All uwsgi processes:")
print(o)
print()

# Find all uwsgi .ini/.conf files on the system
o, _ = run("find /etc /var/www /srv -name '*.ini' -o -name '*.xml' 2>/dev/null | xargs grep -l 'uwsgi\\|wsgi' 2>/dev/null | head -10")
print("uWSGI config files:")
print(o)
print()

# Check what file is being served on port 5000
o, _ = run("ss -tlnp | grep 5000")
print("Port 5000 (uWSGI):", o)
print()

# Check uwsgi configuration
o, _ = run("cat /etc/uwsgi/apps-enabled/*.ini 2>/dev/null || cat /etc/uwsgi/apps-available/*.ini 2>/dev/null | head -30")
print("uWSGI ini config:")
print(o[:500])

import os
ssh.close()
