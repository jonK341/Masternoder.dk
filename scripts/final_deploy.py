import paramiko, os, time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST, USER, PASS = os.environ.get("DEPLOY_HOST", "masternoder.dk"), os.environ.get("DEPLOY_USER", "root"), (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))

def new_ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(HOST, username=USER, password=PASS, timeout=30)
    return s

def run(s, cmd, t=20):
    _, o, _ = s.exec_command(cmd, timeout=t)
    return o.read().decode("utf-8", errors="replace").strip()

def fire(s, cmd):
    try: s.exec_command(cmd, timeout=3)
    except: pass

ssh = new_ssh()
sftp = ssh.open_sftp()

for rel in ["backend/routes/missing_endpoints_routes.py"]:
    local  = os.path.join(BASE, rel.replace("/", os.sep))
    remote = "/var/www/html/" + rel
    sftp.put(local, remote)
    print(f"[OK] {rel} -> ROOT")

run(ssh, "find /var/www/html/backend/routes -name 'missing_endpoints*pyc' -delete 2>/dev/null; find /var/www/html/backend/routes/__pycache__ -delete 2>/dev/null; true", t=8)
fire(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; sleep 3; systemctl start uwsgi-vidgenerator 2>/dev/null")
sftp.close(); ssh.close()

print("Waiting 20s...")
time.sleep(20)

ssh = new_ssh()
print("Service:", run(ssh, "systemctl is-active uwsgi-vidgenerator", t=5))

tests = [
    "/vidgenerator/api/system/overview?compact=1",
    "/vidgenerator/api/agent/automation/ai-diagnose",
    "/vidgenerator/api/leaderboard/top10",
    "/vidgenerator/api/shop/daily-deal",
    "/vidgenerator/api/quests/daily",
]
ok = 0
for ep in tests:
    code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
    if code == "200": ok += 1
    print(f"  {'[OK]' if code=='200' else '[!!]'} [{code}] {ep}")

import os
print(f"\n{ok}/{len(tests)} passed")
ssh.close()
