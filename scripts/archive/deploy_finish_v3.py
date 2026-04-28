"""Deploy finish v3 — correct ROOT paths, no blueprint conflict."""
import os, time, paramiko
from datetime import datetime

HOST = "masternoder.dk"
USER = "root"
PASS = "eD)2[K+[S#m_#$3!"
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = "/var/www/html"

FILES = [
    "backend/routes/missing_endpoints_routes.py",   # has system_overview route
    "backend/register_blueprints.py",               # no duplicate system_overview_bp
    "vidgenerator/debugger/index.html",             # new Mission Control tab
]


def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()


def deploy():
    print("=" * 60)
    print("Deploy Finish v3 — ROOT backend fix")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    for rel in FILES:
        local  = os.path.join(BASE, rel.replace("/", os.sep))
        remote = ROOT + "/" + rel
        run(ssh, "mkdir -p " + remote.rsplit("/", 1)[0])
        sftp.put(local, remote)
        print(f"  [OK]   ROOT/{rel}")

    # Clean ALL pyc caches
    print("\n[CLEANUP] Clearing all pyc caches...")
    run(ssh, "find /var/www/html/backend -name '*.pyc' -delete 2>/dev/null; find /var/www/html/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo done", t=10)
    run(ssh, "find /var/www/html/vidgenerator/backend -name '*.pyc' -delete 2>/dev/null; find /var/www/html/vidgenerator/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo done", t=10)

    print("\n[RELOAD] Restarting uWSGI...")
    run(ssh, "systemctl stop uwsgi", t=10)
    time.sleep(3)
    run(ssh, "systemctl start uwsgi", t=10)
    time.sleep(10)

    print("\n[VERIFY]")
    for ep in [
        "/vidgenerator/api/system/overview?compact=1",
        "/vidgenerator/api/leaderboard/top10",
        "/vidgenerator/api/quests/daily",
        "/vidgenerator/api/shop/daily-deal",
        "/vidgenerator/debugger/",
    ]:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        flag = "[OK]" if code == "200" else "[WARN]"
        print(f"  {flag}  {ep} -> {code}")

    # Payload
    p = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "import sys,json; d=json.load(sys.stdin); h=d.get('health',{}); llm=d.get('llm',{}); vid=d.get('video_providers',[]); print('Health:', h.get('score'), h.get('grade'), '/', h.get('label'), '| LLM:', llm.get('available'), 'ready | Video:', sum(1 for p in vid if p.get('available')), 'ready')" """, t=20)
    if p:
        print(f"\n[OVERVIEW] {p}")

    sftp.close(); ssh.close()
    print("\n" + "=" * 60)
    print("[DONE] Finish deployed!")
    print("Mission Control: https://masternoder.dk/vidgenerator/debugger/")
    print("=" * 60)


if __name__ == "__main__":
    deploy()
