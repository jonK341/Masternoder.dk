"""
Deploy Finish FINAL — restart the correct uwsgi-vidgenerator service.
"""
import os, time, paramiko
from datetime import datetime

HOST = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or os.environ.get("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS"))
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = "/var/www/html"

# Deploy to both locations so Python finds the correct version
FILES = [
    ("backend/routes/missing_endpoints_routes.py", ROOT),
    ("backend/register_blueprints.py",              ROOT),
    ("vidgenerator/debugger/index.html",            ROOT),
]


def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()


def deploy():
    print("=" * 60)
    print("Deploy Finish FINAL — correct service restart")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    for rel, base in FILES:
        local  = os.path.join(BASE, rel.replace("/", os.sep))
        remote = base + "/" + rel
        run(ssh, "mkdir -p " + remote.rsplit("/", 1)[0])
        sftp.put(local, remote)
        print(f"  [OK]  {remote}")

    # Clear ALL pyc caches
    print("\n[CLEANUP] Clearing pyc caches...")
    for d in ["/var/www/html/backend", "/var/www/html/vidgenerator/backend"]:
        run(ssh, f"find {d} -name '*.pyc' -delete 2>/dev/null; find {d} -name '__pycache__' -exec rm -rf {{}} + 2>/dev/null; true")

    # Restart the CORRECT service
    print("\n[RELOAD] Restarting uwsgi-vidgenerator.service...")
    run(ssh, "systemctl stop uwsgi-vidgenerator", t=15)
    time.sleep(3)
    run(ssh, "systemctl start uwsgi-vidgenerator", t=15)
    time.sleep(12)

    # Check service status
    status = run(ssh, "systemctl is-active uwsgi-vidgenerator")
    print(f"  uwsgi-vidgenerator status: {status}")

    print("\n[VERIFY]")
    tests = [
        "/vidgenerator/api/system/overview?compact=1",
        "/vidgenerator/api/leaderboard/top10",
        "/vidgenerator/api/quests/daily",
        "/vidgenerator/api/shop/daily-deal",
        "/vidgenerator/debugger/",
    ]
    all_ok = True
    for ep in tests:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        ok   = code == "200"
        if not ok:
            all_ok = False
        print(f"  {'[OK]' if ok else '[WARN]'}  {ep} -> {code}")

    # Full payload test
    p = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "
import sys,json
d=json.load(sys.stdin)
h=d.get('health',{})
llm=d.get('llm',{})
vid=d.get('video_providers',[])
print('Platform:', d.get('platform'), d.get('version'))
print('Health:', h.get('score'), '/', 100, '(' + h.get('grade','?') + ')', h.get('label',''))
print('LLM:', llm.get('available',0), '/', llm.get('total',0), 'ready')
print('Video:', sum(1 for p in vid if p.get('available')), '/', len(vid), 'ready')
print('Daily deal:', d.get('daily_deal',{}).get('name','(none)'))
print('Quests:', len(d.get('daily_quests',[])), 'active')
" """, t=20)
    if p:
        print(f"\n[OVERVIEW PAYLOAD]\n{p}")

    sftp.close(); ssh.close()
    print("\n" + "=" * 60)
    if all_ok:
        print("[SUCCESS] All endpoints verified!")
    else:
        print("[DONE] Some endpoints need attention.")
    print()
    print("Mission Control is live at:")
    print("  https://masternoder.dk/vidgenerator/debugger/")
    print("  Open the pulsing green 'Mission Control' tab")
    print()
    print("System Overview API:")
    print("  GET https://masternoder.dk/vidgenerator/api/system/overview")
    print("  GET https://masternoder.dk/vidgenerator/api/system/overview?compact=1")
    print("=" * 60)


if __name__ == "__main__":
    deploy()
