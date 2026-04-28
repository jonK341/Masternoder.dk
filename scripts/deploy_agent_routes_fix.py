"""Re-deploy fixed agent_profile_routes and account_resolution_service."""
import paramiko, os, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
sftp = ssh.open_sftp()

files = [
    ("backend/routes/agent_profile_routes.py", "backend/routes/agent_profile_routes.py"),
    ("backend/services/account_resolution_service.py", "backend/services/account_resolution_service.py"),
]
for local_rel, remote_rel in files:
    local = os.path.join(BASE_LOCAL, local_rel)
    if os.path.exists(local):
        sftp.put(local, f"{BASE_REMOTE}/{remote_rel}")
        print(f"  [OK] {os.path.basename(local)}")
    else:
        print(f"  [SKIP] {local_rel} not found locally")

sftp.close()

# Test import
print("\n=== Import test ===")
r = run(ssh, """cd /var/www/html/vidgenerator && python3 -c "
import sys; sys.path.insert(0,'.')
from backend.routes.agent_profile_routes import agent_profile_bp
print('agent_profile_bp OK:', agent_profile_bp.name)
" 2>&1""", timeout=20)
print(r)

# Restart uWSGI
print("\n=== Restarting uWSGI ===")
print(run(ssh, "systemctl restart uwsgi 2>&1 && echo OK", timeout=30))
time.sleep(5)

# Test endpoint
print("\n=== Test endpoints ===")
print(run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user' | head -c 400 2>&1"))
print(run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/activity-feed?user_id=default_user' | head -c 300 2>&1"))

ssh.close()
print("Done.")
