"""Restart the correct service and verify endpoints."""
import paramiko, time, socket

HOST = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))


def new_ssh():
    s = paramiko.SSHClient()
    s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    s.connect(HOST, username=USER, password=PASS, timeout=30)
    return s


def fire(ssh, cmd):
    """Run command, don't wait for output (avoids timeout)."""
    try:
        ssh.exec_command(cmd, timeout=5)
    except Exception:
        pass


def run(ssh, cmd, t=25):
    try:
        _, out, _ = ssh.exec_command(cmd, timeout=t)
        return out.read().decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"[timeout/err: {e}]"


print("Connecting...")
ssh = new_ssh()
print("  Connected.")

# Stop service (fire-and-forget to avoid SSH timeout)
print("Stopping uwsgi-vidgenerator (fire-and-forget)...")
fire(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null; sleep 2; systemctl start uwsgi-vidgenerator 2>/dev/null &")
ssh.close()

print("Waiting 15s for service to restart...")
time.sleep(15)

ssh = new_ssh()

status = run(ssh, "systemctl is-active uwsgi-vidgenerator", t=10)
pids   = run(ssh, "ps aux | grep 'uwsgi.*vidgenerator' | grep -v grep | wc -l", t=10)
print(f"  Service: {status}  |  Workers: {pids}")

print("\nVerifying endpoints...")
eps = [
    "/vidgenerator/api/system/overview?compact=1",
    "/vidgenerator/api/leaderboard/top10",
    "/vidgenerator/api/quests/daily",
    "/vidgenerator/api/shop/daily-deal",
    "/vidgenerator/debugger/",
]
for ep in eps:
    code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
    print(f"  {'[OK]' if code == '200' else '[WARN]'}  {ep} -> {code}")

p = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "import sys,json;d=json.load(sys.stdin);h=d.get('health',{});print('Health:',h.get('score'),h.get('grade'),h.get('label'),'| LLM:',d.get('llm',{}).get('available'),'ready')" """, t=20)
print(f"\n  Overview: {p}")

import os
ssh.close()
print("\nDone.")
