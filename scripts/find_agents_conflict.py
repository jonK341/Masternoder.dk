"""Find what's registering /agents/ -> None endpoint."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=30):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    # Search ALL route files for /agents
    print("=== All routes referencing /agents ===")
    out = run_cmd(ssh, f"grep -rn \"/agents\" {BASE_REMOTE}/backend/routes/*.py 2>/dev/null | grep -v '.pyc'")
    print(out)

    # Check the url map directly from a running Python context
    print("\n=== URL map for /agents URLs ===")
    out = run_cmd(ssh, f"""cd {BASE_REMOTE} && .venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from src.app import create_app
app = create_app()
rules = [(r.rule, r.endpoint) for r in app.url_map.iter_rules() if 'agent' in r.rule.lower()]
for rule, ep in sorted(rules):
    vf = app.view_functions.get(ep)
    print(rule, '->', ep, '->', vf)
" 2>&1 | grep -E "agent|ERROR" | head -40""", timeout=30)
    print(out)

    # What file is currently on server
    print("\n=== Last lines of all_page_routes.py on server ===")
    out = run_cmd(ssh, f"tail -30 {BASE_REMOTE}/backend/routes/all_page_routes.py")
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()
