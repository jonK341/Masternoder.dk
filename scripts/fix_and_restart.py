import paramiko, time, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def new_ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(HOST, username=USER, password=PASS, timeout=30)
    return s

def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()

def fire(ssh, cmd):
    try:
        ssh.exec_command(cmd, timeout=3)
    except Exception:
        pass

ssh = new_ssh()
sftp = ssh.open_sftp()
print("Connected.")

# Upload fixed leaderboard_routes.py to ROOT
local  = os.path.join(BASE, "backend", "routes", "leaderboard_routes.py")
remote = "/var/www/html/backend/routes/leaderboard_routes.py"
sftp.put(local, remote)
print("  [OK] leaderboard_routes.py -> ROOT")

# Clear pyc
run(ssh, "find /var/www/html/backend/routes -name '*.pyc' -delete 2>/dev/null; find /var/www/html/backend/routes -name '__pycache__' -exec rm -rf {} + 2>/dev/null; true", t=8)

# Restart correct service (fire-and-forget)
fire(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; sleep 3; systemctl start uwsgi-vidgenerator 2>/dev/null")
sftp.close()
ssh.close()

print("Waiting 20s...")
time.sleep(20)

ssh = new_ssh()
status = run(ssh, "systemctl is-active uwsgi-vidgenerator", t=8)
print(f"Service: {status}")

endpoints = [
    "/vidgenerator/api/system/overview?compact=1",
    "/vidgenerator/api/leaderboard/top10",
    "/vidgenerator/api/leaderboard",
    "/vidgenerator/api/quests/daily",
    "/vidgenerator/api/shop/daily-deal",
    "/vidgenerator/api/agent/automation/ai-diagnose",
    "/vidgenerator/api/ai/video-providers",
    "/vidgenerator/debugger/",
]
print("\nEndpoints:")
for ep in endpoints:
    code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
    print(f"  {'[OK]' if code == '200' else '[!!]'}  {ep} -> {code}")

import os
p = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "import sys,json;d=json.load(sys.stdin);h=d.get('health',{});llm=d.get('llm',{});vid=d.get('video_providers',[]);print('Health:',h.get('score'),h.get('grade'),'-',h.get('label'));print('LLM:',llm.get('available'),'ready | Video:',sum(1 for p in vid if p.get('available')),'ready')" """, t=20)
print(f"\n{p}")
ssh.close()
