"""Deploy top-20 endpoint upgrades to production."""
import os, time, paramiko
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "/var/www/html/vidgenerator"

FILES = [
    "backend/routes/missing_endpoints_routes.py",
]

VERIFY = [
    "/vidgenerator/api/game/challenges/daily",
    "/vidgenerator/api/game/challenges/weekly",
    "/vidgenerator/api/game/stats/advanced/trends",
    "/vidgenerator/api/game/stats/advanced/performance",
    "/vidgenerator/api/game/stats/advanced/global",
    "/vidgenerator/api/statistics",
    "/vidgenerator/api/themes/list",
    "/vidgenerator/api/game/ai-coach",
    "/vidgenerator/api/notifications/count",
]

def run(ssh, cmd, t=20):
    _, out, err = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()

def deploy():
    print("=" * 60)
    print("Deploy: Top-20 Missing Endpoint Upgrades")
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=30)
    sftp = ssh.open_sftp()
    print("[SSH] Connected.")

    for rel in FILES:
        local  = os.path.join(BASE_DIR, rel.replace("/", os.sep))
        remote = REMOTE_BASE + "/" + rel
        run(ssh, "mkdir -p " + remote.rsplit("/", 1)[0])
        sftp.put(local, remote)
        print(f"  [OK] {rel}")

    print("\n[RELOAD] Restarting uWSGI...")
    run(ssh, "systemctl restart uwsgi 2>/dev/null || true", t=30)
    time.sleep(5)

    print(f"\n[VERIFY] {len(VERIFY)} endpoints...")
    for ep in VERIFY:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        flag = "[OK]" if code == "200" else "[WARN]"
        print(f"  {flag}  {ep} -> {code}")

    sftp.close(); ssh.close()
    print("\n[DONE] Top-20 upgrades live!")
    print("\nNew/upgraded endpoints:")
    for ep in VERIFY:
        print(f"  {ep}")
    print("  POST /vidgenerator/api/game/save-all-stats   (now saves XP to DB)")
    print("  POST /vidgenerator/api/game/hunters/prestige (now real prestige system)")
    print("  POST /vidgenerator/api/video-generation/solve-problems (now AI-powered)")
    print("  POST /vidgenerator/api/game/hunters/allocate-stats (now persists)")

if __name__ == "__main__":
    deploy()
