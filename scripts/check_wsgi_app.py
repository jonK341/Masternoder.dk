"""Check wsgi.py to understand how the app is created."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== wsgi.py ===")
print(run(ssh, f"cat {BASE_REMOTE}/wsgi.py"))

print("\n=== uwsgi log tail (startup) ===")
print(run(ssh, f"head -60 {BASE_REMOTE}/uwsgi.log 2>/dev/null || tail -60 {BASE_REMOTE}/uwsgi.log 2>/dev/null | head -40"))

print("\n=== Check routes in running worker ===")
# Hit an endpoint that we know exists to see which routes are loaded
print(run(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/points/all?user_id=default_user' 2>&1 | head -c 200"))

ssh.close()
