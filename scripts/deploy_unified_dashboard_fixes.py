"""Deploy unified dashboard fixes: points API, static route, service worker defer."""
import paramiko
import os
import sys

SERVER = "masternoder.dk"
USER = "root"
PASS = (os.getenv("DEPLOY_PASS") or "").strip() or (_ for _ in ()).throw(SystemExit("Set DEPLOY_PASS for SSH."))
REMOTE_BASE = "/var/www/html"
LOCAL_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FILES = [
    "backend/routes/missing_endpoints_routes.py",
    "backend/routes/all_page_routes.py",
    "vidgenerator/static/js/enhanced-frontpage-stats.js",
    "vidgenerator/static/js/trigger-based-actions.js",
    "vidgenerator/static/js/service-worker-gatherer.js",
    "vidgenerator/service-worker.js",
]


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER, username=USER, password=PASS, timeout=15)
    sftp = ssh.open_sftp()

    print("Deploying unified dashboard fixes to", REMOTE_BASE)
    for f in FILES:
        local = os.path.join(LOCAL_BASE, f.replace("/", os.sep))
        remote = f"{REMOTE_BASE}/{f}"
        if not os.path.exists(local):
            print(f"  SKIP (not found): {f}")
            continue
        remote_dir = remote.rsplit("/", 1)[0]
        ssh.exec_command(f"mkdir -p {remote_dir}")
        sftp.put(local, remote)
        print(f"  OK {f}")

    sftp.close()
    ssh.close()
    print("\nDeploy done. Running restart...")
    import subprocess
    ok = subprocess.call(
        [sys.executable, os.path.join(LOCAL_BASE, "restart_flask_app.py")],
        cwd=LOCAL_BASE,
    )
    sys.exit(ok)


if __name__ == "__main__":
    main()
