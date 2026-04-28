"""Deploy agent routes via missing_endpoints_routes.py (guaranteed to load)."""
import paramiko, os, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_ROOT = "/var/www/html"

def run(ssh, cmd, timeout=30):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
sftp = ssh.open_sftp()

FILES = [
    ("backend/routes/missing_endpoints_routes.py", "backend/routes/missing_endpoints_routes.py"),
    ("backend/services/agent_db_service.py",        "backend/services/agent_db_service.py"),
    ("backend/services/user_agent_skills.py",       "backend/services/user_agent_skills.py"),
]
print("=== Uploading ===")
for local_rel, remote_rel in FILES:
    local = os.path.join(BASE_LOCAL, local_rel)
    sftp.put(local, f"{SERVER_ROOT}/{remote_rel}")
    print(f"  [OK] {remote_rel}")
sftp.close()

# Clear pycache for these specific files
print("\n=== Clear pycache ===")
print(run(ssh, f"find {SERVER_ROOT}/backend -name '*.pyc' -delete 2>/dev/null && echo cleared"))

# Restart
print("\n=== Restart uWSGI ===")
print(run(ssh, "systemctl stop uwsgi && sleep 2 && systemctl start uwsgi && echo restarted", timeout=30))
time.sleep(8)

print("Status:", run(ssh, "systemctl is-active uwsgi"))

# Test
print("\n=== Live test ===")
r1 = run(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500")
print("my-agents:", r1)
r2 = run(ssh, "curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/activity-feed?user_id=default_user' 2>&1 | head -c 300")
print("activity-feed:", r2)

print("\n=== HTTPS test ===")
print(run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500"))

ssh.close()
print("\nDone.")
