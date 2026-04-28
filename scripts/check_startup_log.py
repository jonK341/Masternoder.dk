"""Check uWSGI startup log to see if agent_profile is registered."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

# Get last 200 lines of uwsgi.log to see startup
print("=== Last uwsgi.log lines ===")
print(run(ssh, "tail -150 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | grep -E 'agent_profile|agent_db|Registered|WARN|ERROR|SUMMARY' | tail -30"))

print("\n=== Does running app have agent_profile route? ===")
r = run(ssh, """cd /var/www/html && python3 -c "
import sys; sys.path.insert(0,'.')
from src.app import create_app
app = create_app()
with app.app_context():
    agent_routes = [str(r) for r in app.url_map.iter_rules() if 'agents/my' in str(r) or 'agents/activ' in str(r)]
    print('Agent routes:', agent_routes)
    print('Total:', len(list(app.url_map.iter_rules())))
" 2>&1 | tail -5""", timeout=25)
print(r)

print("\n=== Check register_blueprints.py has agent_profile ===")
print(run(ssh, "grep -n 'agent_profile' /var/www/html/backend/register_blueprints.py | head -5"))

ssh.close()
