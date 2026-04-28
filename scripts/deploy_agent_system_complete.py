"""Deploy complete agent system fix — registers routes, adds hooks, creates agents page."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

FILES = [
    # Backend
    ("backend/register_blueprints.py", f"{BASE_REMOTE}/backend/register_blueprints.py"),
    ("backend/routes/all_page_routes.py", f"{BASE_REMOTE}/backend/routes/all_page_routes.py"),
    ("backend/routes/shop_routes.py", f"{BASE_REMOTE}/backend/routes/shop_routes.py"),
    ("backend/routes/hunters_game.py", f"{BASE_REMOTE}/backend/routes/hunters_game.py"),
    ("backend/services/agent_db_service.py", f"{BASE_REMOTE}/backend/services/agent_db_service.py"),
    ("backend/routes/agent_profile_routes.py", f"{BASE_REMOTE}/backend/routes/agent_profile_routes.py"),
    # Frontend
    ("vidgenerator/profile/index.html", f"{BASE_REMOTE}/vidgenerator/profile/index.html"),
    ("vidgenerator/agents/index.html", f"{BASE_REMOTE}/vidgenerator/agents/index.html"),
]

def run_cmd(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    # Ensure agents dir exists on server
    out, err = run_cmd(ssh, f"mkdir -p {BASE_REMOTE}/vidgenerator/agents")
    print(f"mkdir agents: {out or 'ok'} {err or ''}")

    print("\n=== Uploading files ===")
    for local_rel, remote in FILES:
        local = os.path.join(BASE_LOCAL, local_rel)
        if not os.path.exists(local):
            print(f"  SKIP (not found): {local_rel}")
            continue
        sftp.put(local, remote)
        print(f"  Uploaded: {os.path.basename(local)}")

    sftp.close()

    # Restart uWSGI to pick up blueprint changes
    print("\n=== Restarting uWSGI ===")
    out, err = run_cmd(ssh, "systemctl reload vidgenerator 2>/dev/null || systemctl restart vidgenerator 2>/dev/null || touch /var/www/html/vidgenerator/uwsgi.ini", timeout=25)
    print(f"  {out or ''} {err or ''}")

    out2, _ = run_cmd(ssh, "systemctl is-active vidgenerator 2>/dev/null || echo unknown")
    print(f"  Service status: {out2}")

    ssh.close()
    print("\nDone.")

if __name__ == "__main__":
    main()
