import paramiko, time

HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

for _ in range(8):
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=20)

    def run(cmd, t=20):
        _, o, _ = ssh.exec_command(cmd, timeout=t)
        return o.read().decode('utf-8', errors='replace').strip()

    s = run("systemctl is-active uwsgi-vidgenerator", t=5)
    w = run("ps aux | grep 'uwsgi.*vidgenerator' | grep -v grep | wc -l", t=5)
    print(f"Service: {s}  Workers: {w}")
    ssh.close()
    if s == "active" and int(w) >= 4:
        break
    time.sleep(5)

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(HOST, username=USER, password=PASS, timeout=20)

def run(cmd, t=20):
    _, o, _ = ssh.exec_command(cmd, timeout=t)
    return o.read().decode('utf-8', errors='replace').strip()

o = run("curl -s 'https://masternoder.dk/vidgenerator/api/user/ai-analysis?user_id=default_user' --max-time 15 -w '\\nSTATUS:%{http_code}'", t=20)
print("User AI Analysis response:", o[:300])

# Also test via POST
o = run("""curl -s -X POST 'https://masternoder.dk/vidgenerator/api/user/ai-analysis' -H 'Content-Type: application/json' -d '{"user_id":"default_user"}' --max-time 15 -w '\\nSTATUS:%{http_code}'""", t=20)
print("POST response:", o[:300])

import os
ssh.close()
