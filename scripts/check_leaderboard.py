import paramiko, time
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect('masternoder.dk', username='root', password=(os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS")), timeout=20)

def run(cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode('utf-8', errors='replace').strip()

# Wait for service to be active
for _ in range(3):
    s = run("systemctl is-active uwsgi-vidgenerator", t=5)
    print("Service:", s)
    if s == "active":
        break
    time.sleep(5)

# Get the leaderboard error
o = run("curl -s 'https://masternoder.dk/vidgenerator/api/leaderboard/top10' --max-time 15", t=20)
print("\nLeaderboard top10:", o[:500])

o = run("curl -s 'https://masternoder.dk/vidgenerator/api/leaderboard' --max-time 15", t=20)
print("\nLeaderboard base:", o[:200])

# Final overview
o = run("curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c \"import sys,json;d=json.load(sys.stdin);h=d.get('health',{});print('Health:',h.get('score'),h.get('grade'),'-',h.get('label'))\"", t=20)
print("\nOverview health:", o)

import os
ssh.close()
