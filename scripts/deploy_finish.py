"""Deploy the nice finish — Mission Control."""
import os, time, paramiko
from datetime import datetime

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE_BASE = "/var/www/html/vidgenerator"

FILES = [
    "backend/routes/system_overview_routes.py",
    "backend/routes/missing_endpoints_routes.py",
    "backend/register_blueprints.py",
    "vidgenerator/debugger/index.html",
]

VERIFY = [
    "/vidgenerator/api/system/overview?compact=1",
    "/vidgenerator/debugger/",
]

def run(ssh, cmd, t=20):
    _, out, _ = ssh.exec_command(cmd, timeout=t)
    return out.read().decode("utf-8", errors="replace").strip()

def deploy():
    print("=" * 60)
    print("Deploy: Nice Finish — Mission Control")
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
        print(f"  [OK]   {rel}")

    print("\n[RELOAD] Restarting uWSGI...")
    run(ssh, "systemctl restart uwsgi 2>/dev/null || true", t=30)
    time.sleep(5)

    print(f"\n[VERIFY] {len(VERIFY)} endpoints...")
    for ep in VERIFY:
        code = run(ssh, f"curl -s -o /dev/null -w '%{{http_code}}' 'https://masternoder.dk{ep}' --max-time 12", t=20)
        flag = "[OK]" if code in ("200","301","302") else "[WARN]"
        print(f"  {flag}  {ep} -> {code}")

    # Quick payload check on overview
    payload = run(ssh, "curl -s 'https://masternoder.dk/vidgenerator/api/system/overview?compact=1' --max-time 15 | python3 -c \"import sys,json; d=json.load(sys.stdin); h=d.get('health',{}); print('Health:', h.get('score'), h.get('grade'), '|', 'LLM:', d.get('llm',{}).get('available'), 'ready |', 'Video:', sum(1 for p in d.get('video_providers',[]) if p.get('available')), 'ready')\"", t=25)
    if payload:
        print(f"\n[OVERVIEW] {payload}")

    sftp.close(); ssh.close()
    print("\n" + "=" * 60)
    print("[DONE] Nice finish deployed!")
    print("=" * 60)
    print("\nMission Control live at:")
    print("  https://masternoder.dk/vidgenerator/debugger/")
    print("  -> Open the 'Mission Control' tab (top left, pulsing green)")
    print("\nSystem Overview API:")
    print("  GET https://masternoder.dk/vidgenerator/api/system/overview")
    print("  GET https://masternoder.dk/vidgenerator/api/system/overview?compact=1")

if __name__ == "__main__":
    deploy()
