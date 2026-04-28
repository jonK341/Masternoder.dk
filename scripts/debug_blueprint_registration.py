"""Debug blueprint registration on server."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run(ssh, cmd, timeout=30):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

# Check if register_blueprints is actually being called
print("=== Check register_blueprints has agent_profile ===")
print(run(ssh, f"grep -n 'agent_profile' {BASE_REMOTE}/backend/register_blueprints.py | head -5"))

# Run full app startup to see what registers
print("\n=== Check registered routes ===")
r = run(ssh, f"""cd {BASE_REMOTE} && python3 -c "
import sys; sys.path.insert(0,'.')
from src.db.models import db
from src.app import create_app
app = create_app()
with app.app_context():
    routes = [str(r) for r in app.url_map.iter_rules() if 'agent' in str(r)]
    print('Agent routes found:', len(routes))
    for r in sorted(routes)[:20]:
        print(' ', r)
" 2>&1""", timeout=25)
print(r[:2000])

# Check logs
print("\n=== uwsgi app error log ===")
print(run(ssh, f"tail -30 /var/log/uwsgi/app/*.log 2>/dev/null | grep -i 'agent_profile\\|error\\|warn' | tail -15 || echo 'no log'"))

ssh.close()
