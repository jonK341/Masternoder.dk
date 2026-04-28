"""Deploy full agent system: DB service, profile routes, profile page, wired point triggers."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"


def run_cmd(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err


FILES = [
    # New service
    ("backend/services/agent_db_service.py",         "backend/services/agent_db_service.py"),
    # New routes
    ("backend/routes/agent_profile_routes.py",       "backend/routes/agent_profile_routes.py"),
    # Updated services/routes
    ("backend/services/video_generator_service.py",  "backend/services/video_generator_service.py"),
    ("backend/routes/quest_routes.py",               "backend/routes/quest_routes.py"),
    ("backend/routes/hunters_game.py",               "backend/routes/hunters_game.py"),
    ("backend/register_blueprints.py",               "backend/register_blueprints.py"),
    # Profile page
    ("vidgenerator/profile/index.html",              "profile/index.html"),
]


def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    print("=== Uploading agent system files ===")
    for local_rel, remote_rel in FILES:
        local = os.path.join(BASE_LOCAL, local_rel)
        remote = f"{BASE_REMOTE}/{remote_rel}"
        sftp.put(local, remote)
        print(f"  [OK] {os.path.basename(local)}")

    sftp.close()

    # Create logs/agent_progress dir on server
    print("\n=== Ensuring log directories ===")
    out, err = run_cmd(ssh, "mkdir -p /var/www/html/vidgenerator/logs/agent_progress && echo ok")
    print(f"  mkdir agent_progress: {out or err}")

    # Restart uWSGI to pick up new routes and service
    print("\n=== Restarting uWSGI ===")
    out, err = run_cmd(ssh, "systemctl reload uwsgi 2>&1 || systemctl restart uwsgi 2>&1 || echo 'reload attempted'", timeout=30)
    print(f"  uwsgi: {out or err}")

    import time
    time.sleep(3)

    # Quick smoke test
    print("\n=== Smoke test: /api/agents/my-agents ===")
    out, err = run_cmd(ssh, "curl -s 'http://localhost/vidgenerator/api/agents/my-agents?user_id=default_user' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('success:', d.get('success'), '| agents:', len(d.get('agents',[])))\" 2>&1", timeout=15)
    print(f"  {out or err}")

    print("\n=== Smoke test: /api/agents/activity-feed ===")
    out, err = run_cmd(ssh, "curl -s 'http://localhost/vidgenerator/api/agents/activity-feed?user_id=default_user' | python3 -c \"import sys,json; d=json.load(sys.stdin); print('success:', d.get('success'), '| activities:', len(d.get('activities',[])))\" 2>&1", timeout=15)
    print(f"  {out or err}")

    ssh.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
