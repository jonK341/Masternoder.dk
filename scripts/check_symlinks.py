import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# Check if backend is a symlink
o, _ = run("ls -la /var/www/html/vidgenerator/ | head -20")
print("vidgenerator dir:")
print(o)
print()
o, _ = run("ls -la /var/www/html/ | head -15")
print("html root:")
print(o)
print()

# Check line count of BOTH missing_endpoints files
o, _ = run("wc -l /var/www/html/backend/routes/missing_endpoints_routes.py /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py 2>/dev/null")
print("Line counts:", o)
print()

# Check if leaderboard exists in the imported location
o, _ = run("ls -la /var/www/html/backend/routes/leaderboard_routes.py 2>/dev/null || echo NOT FOUND")
print("leaderboard at html/backend:", o)
o, _ = run("ls -la /var/www/html/vidgenerator/backend/routes/leaderboard_routes.py 2>/dev/null || echo NOT FOUND")
print("leaderboard at vidgenerator/backend:", o)

import os
ssh.close()
