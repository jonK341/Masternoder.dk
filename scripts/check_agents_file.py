"""Check agents html file and Flask app name."""
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

    print("=== agents/index.html on server ===")
    out = run_cmd(ssh, f"ls -la {BASE_REMOTE}/vidgenerator/agents/ 2>/dev/null || echo 'dir does not exist'")
    print(out)

    print("\n=== Flask app name ===")
    out = run_cmd(ssh, f"grep -n 'Flask(' {BASE_REMOTE}/src/app.py 2>/dev/null | head -5")
    print(out)

    print("\n=== _base_path() function ===")
    out = run_cmd(ssh, f"grep -n '_base_path\\|BASE_PATH\\|base_path' {BASE_REMOTE}/backend/routes/all_page_routes.py | head -10")
    print(out)

    # Test the actual function directly
    print("\n=== Test agents_page function directly ===")
    out = run_cmd(ssh, f"""cd {BASE_REMOTE} && .venv/bin/python -c "
import sys
sys.path.insert(0, '.')
from backend.routes.all_page_routes import agents_page
# Test calling it in a request context
from src.app import create_app
app = create_app()
with app.test_request_context('/agents/'):
    result = agents_page()
    print('Result type:', type(result))
    if result is None:
        print('RETURNS NONE!')
    else:
        print('Returns:', str(result)[:100])
" 2>&1 | tail -10""", timeout=20)
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()
