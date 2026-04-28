"""
Deploy the nice finish — copy updated files to the ROOT /var/www/html/backend/
location that Python actually imports from, then restart.
"""
import os, time, paramiko
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID_ROOT    = "/var/www/html/vidgenerator"    # already deployed here
ROOT        = "/var/www/html"                 # Python imports from here

# Files that need to land in the ROOT backend/ for Python to pick them up
# (relative to backend/ dir)
ROOT_FILES = [
    "backend/routes/missing_endpoints_routes.py",
    "backend/routes/system_overview_routes.py",
    "backend/register_blueprints.py",
]


def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()


def deploy():
    print("=" * 60)
    print("Deploy v2: Fix ROOT paths")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    # Upload to ROOT location
    for rel in ROOT_FILES:
        local  = os.path.join(BASE_DIR, rel.replace("/", os.sep))
        remote = ROOT + "/" + rel
        run(ssh, "mkdir -p " + remote.rsplit("/", 1)[0])
        sftp.put(local, remote)
        print(f"  [OK]   ROOT/{rel}")

    # Clear pyc cache at ROOT/backend
    print("\n[CLEANUP] Clearing pyc cache at ROOT/backend...")
    run(ssh, "find /var/www/html/backend -name '*.pyc' -delete && find /var/www/html/backend -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null; echo done")

    print("\n[RELOAD] Full stop/start of uWSGI...")
    run(ssh, "systemctl stop uwsgi", t=10)
    time.sleep(3)
    run(ssh, "systemctl start uwsgi", t=10)
    time.sleep(8)

    print("\n[VERIFY] Testing endpoints...")
    tests = [
        ("/vidgenerator/api/system/overview?compact=1", "200"),
        ("/vidgenerator/api/leaderboard/top10", "200"),
        ("/vidgenerator/api/quests/daily", "200"),
        ("/vidgenerator/debugger/", "200"),
    ]
    all_ok = True
    for ep, want in tests:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        flag = "[OK]" if code == want else "[WARN]"
        if code != want:
            all_ok = False
        print(f"  {flag}  {ep} -> {code}")

    # Payload check
    payload = run(ssh, """curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c "import sys,json; d=json.load(sys.stdin); h=d.get('health',{}); print('Health:', h.get('score'), h.get('grade'), h.get('label'), '| LLM ready:', d.get('llm',{}).get('available'))" """, t=20)
    print(f"\n[OVERVIEW] {payload}")

    sftp.close(); ssh.close()
    print("\n" + "=" * 60)
    if all_ok:
        print("[DONE] Deployment complete!")
    else:
        print("[DONE] Deployment done with warnings.")
    print("=" * 60)


if __name__ == "__main__":
    deploy()
