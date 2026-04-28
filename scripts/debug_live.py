import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip(), err.read().decode('utf-8', errors='replace').strip()

# Where does route_loader.py live?
o, _ = run("find /var/www/html -name 'route_loader.py' 2>/dev/null")
print("route_loader.py locations:", o)

# Test the LIVE endpoint directly on localhost (port 5000)
o, _ = run("curl -v 'http://localhost:5000/vidgenerator/api/system/overview?compact=1' --max-time 10 2>&1 | tail -20")
print("\nLive localhost test:")
print(o[:1000])

# Test without /vidgenerator prefix
o, _ = run("curl -s 'http://localhost:5000/api/system/overview?compact=1' --max-time 10 -w '\\nSTATUS:%{http_code}'")
print("\nDirect /api/ test:", o[:300])

import os
ssh.close()
