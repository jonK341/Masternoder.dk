"""Debug the /agents/ route conflict."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    # Show exactly what's in all_page_routes for the endpoint registration
    print("=== all_page_routes.py endpoint lines ===")
    out = run_cmd(ssh, f"grep -n 'endpoint\\|def page' {BASE_REMOTE}/backend/routes/all_page_routes.py | head -20")
    print(out)

    # Check if /agents/ is registered anywhere else
    print("\n=== Other routes matching /agents ===")
    out = run_cmd(ssh, f"grep -rn \"route.*'/agents\" {BASE_REMOTE}/backend/routes/*.py 2>/dev/null | grep -v all_page | head -20")
    print(out)

    # Check Python syntax of all_page_routes
    print("\n=== Python syntax check ===")
    out = run_cmd(ssh, f"cd {BASE_REMOTE} && .venv/bin/python -c \"import backend.routes.all_page_routes\" 2>&1")
    print(out or "OK - no syntax errors")

    # Show all registered blueprints that handle /agents
    print("\n=== Full blueprint registration for agents ===")
    out = run_cmd(ssh, f"grep -n 'agents' {BASE_REMOTE}/backend/routes/all_page_routes.py")
    print(out)

    # Show what /agents/ resolves to in the app
    print("\n=== Test app URL map ===")
    out = run_cmd(ssh, f"""cd {BASE_REMOTE} && .venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from src.app import create_app
app = create_app()
with app.app_context():
    rules = [r for r in app.url_map.iter_rules() if 'agents' in r.rule]
    for r in sorted(rules, key=lambda x: x.rule):
        print(r.rule, '->', r.endpoint, '->', app.view_functions.get(r.endpoint))
" 2>&1 | head -30""")
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()
