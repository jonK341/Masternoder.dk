"""Check what agent routes are registered."""
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

r = run(ssh, f"""cd {BASE_REMOTE} && python3 -c "
import sys; sys.path.insert(0,'.')
from src.app import create_app
app = create_app()
with app.app_context():
    routes = [str(r) for r in app.url_map.iter_rules() if 'agent' in str(r).lower() and 'my-agents' in str(r).lower() or 'activity-feed' in str(r).lower()]
    print('Matching routes:')
    for r2 in sorted(routes):
        print(' ', r2)
" 2>&1""", timeout=25)
print(r[-2000:])
ssh.close()
