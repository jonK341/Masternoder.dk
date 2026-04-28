"""Upload remaining files with correct credentials and hard-restart uWSGI."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

FILES = [
    ("backend/routes/all_page_routes.py",   f"{BASE_REMOTE}/backend/routes/all_page_routes.py"),
    ("backend/register_blueprints.py",       f"{BASE_REMOTE}/backend/register_blueprints.py"),
    ("backend/services/agent_db_service.py", f"{BASE_REMOTE}/backend/services/agent_db_service.py"),
    ("backend/routes/agent_profile_routes.py", f"{BASE_REMOTE}/backend/routes/agent_profile_routes.py"),
    ("backend/routes/shop_routes.py",        f"{BASE_REMOTE}/backend/routes/shop_routes.py"),
    ("backend/routes/hunters_game.py",       f"{BASE_REMOTE}/backend/routes/hunters_game.py"),
    ("vidgenerator/profile/index.html",      f"{BASE_REMOTE}/vidgenerator/profile/index.html"),
    ("vidgenerator/agents/index.html",       f"{BASE_REMOTE}/vidgenerator/agents/index.html"),
]

def run(ssh, cmd, timeout=30):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip(), e.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    # Ensure agents dir exists
    run(ssh, f"mkdir -p {BASE_REMOTE}/vidgenerator/agents")

    print("=== Uploading files ===")
    for local_rel, remote in FILES:
        local = os.path.join(BASE_LOCAL, local_rel)
        sftp.put(local, remote)
        print(f"  OK  {os.path.basename(local)}")
    sftp.close()

    print("\n=== Hard-restarting uWSGI ===")
    # Kill all uwsgi workers, systemd will restart them
    out, err = run(ssh, "systemctl restart vidgenerator 2>&1", timeout=20)
    print(f"  systemctl restart: {out or 'ok'} {err or ''}")

    print("  Waiting 8s for workers to come up...")
    time.sleep(8)

    out, _ = run(ssh, "systemctl is-active vidgenerator 2>/dev/null")
    print(f"  Service status: {out}")

    out, _ = run(ssh, "ps aux | grep -c '[u]wsgi'")
    print(f"  uWSGI processes: {out}")

    print("\n=== Smoke tests ===")
    tests = [
        ("GET", "https://masternoder.dk/vidgenerator/agents/"),
        ("GET", "https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user"),
        ("GET", "https://masternoder.dk/vidgenerator/api/agents/activity-feed?user_id=default_user"),
    ]
    for method, url in tests:
        out, _ = run(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        status = out.strip()
        icon = "OK" if status in ("200", "301", "302") else "FAIL"
        print(f"  {icon} [{status}] {url}")

    ssh.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
