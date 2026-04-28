"""Check if any catch-all routes conflict with agent routes."""
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

# Test with direct uwsgi socket to bypass nginx
print("=== Direct WSGI test (bypass nginx) ===")
print(run(ssh, "curl -s --unix-socket /run/uwsgi/app/vidgenerator/socket 'http://localhost/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500 || echo 'direct test failed'"))

# Find the socket
print("\n=== Find socket ===")
print(run(ssh, "find /run/uwsgi /var/run/uwsgi -name '*.socket' 2>/dev/null || echo none"))
print(run(ssh, "ls /var/www/html/vidgenerator/uwsgi.ini"))
print(run(ssh, "cat /var/www/html/vidgenerator/uwsgi.ini | head -20"))

# Check if test_request_context works
print("\n=== Test route matching in app context ===")
r = run(ssh, f"""cd {BASE_REMOTE} && python3 -c "
import sys; sys.path.insert(0,'.')
from src.app import create_app
app = create_app()
with app.test_request_context('/vidgenerator/api/agents/my-agents?user_id=default_user'):
    from flask import request, url_for
    adapter = app.url_map.bind('localhost')
    try:
        endpoint, args = adapter.match('/vidgenerator/api/agents/my-agents', 'GET')
        print('Matched endpoint:', endpoint, 'args:', args)
    except Exception as e:
        print('No match:', e)
" 2>&1""", timeout=25)
print(r[-1500:])
ssh.close()
