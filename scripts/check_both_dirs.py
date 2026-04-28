import paramiko
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode().strip(), err.read().decode().strip()

# List which route files exist in /var/www/html/backend/routes vs vidgenerator/backend/routes
o, _ = run("ls /var/www/html/backend/routes/ | grep -E 'ai_providers|gallery|quest|leaderboard|shop|agent_auto|tts|system_overview'")
print("ROOT /backend/routes files:")
print(o or "(none of the recent AI files)")
print()

o, _ = run("ls /var/www/html/vidgenerator/backend/routes/ | grep -E 'ai_providers|gallery|quest|leaderboard|shop|agent_auto|tts|system_overview'")
print("vidgenerator/backend/routes files:")
print(o)
print()

# For missing_endpoints specifically
o, _ = run("diff <(head -5 /var/www/html/backend/routes/missing_endpoints_routes.py) <(head -5 /var/www/html/vidgenerator/backend/routes/missing_endpoints_routes.py) 2>/dev/null || echo DIFFERENT")
print("Missing endpoints diff (first 5 lines):", o)

import os
ssh.close()
