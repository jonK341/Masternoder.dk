"""
Deploy agent system files to the CORRECT server location:
/var/www/html/backend/ (not /var/www/html/vidgenerator/backend/)
/var/www/html/vidgenerator/ for HTML files
"""
import paramiko, os, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Correct server root
SERVER_ROOT = "/var/www/html"

def run(ssh, cmd, timeout=30):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
sftp = ssh.open_sftp()

# Map: local path → remote path (relative to /var/www/html)
FILES = [
    ("backend/services/agent_db_service.py",        "backend/services/agent_db_service.py"),
    ("backend/routes/agent_profile_routes.py",      "backend/routes/agent_profile_routes.py"),
    ("backend/services/video_generator_service.py", "backend/services/video_generator_service.py"),
    ("backend/routes/quest_routes.py",              "backend/routes/quest_routes.py"),
    ("backend/routes/hunters_game.py",              "backend/routes/hunters_game.py"),
    ("backend/register_blueprints.py",              "backend/register_blueprints.py"),
    ("backend/services/account_resolution_service.py", "backend/services/account_resolution_service.py"),
]

print("=== Uploading to correct server root: /var/www/html ===")
for local_rel, remote_rel in FILES:
    local = os.path.join(BASE_LOCAL, local_rel)
    remote = f"{SERVER_ROOT}/{remote_rel}"
    if os.path.exists(local):
        sftp.put(local, remote)
        print(f"  [OK] {remote_rel}")
    else:
        print(f"  [SKIP] {local_rel} not found locally")

# HTML to correct vidgenerator dir
local_html = os.path.join(BASE_LOCAL, "vidgenerator/profile/index.html")
remote_html = f"{SERVER_ROOT}/vidgenerator/profile/index.html"
sftp.put(local_html, remote_html)
print(f"  [OK] vidgenerator/profile/index.html")

sftp.close()

# Ensure logs dir
print("\n=== Ensuring directories ===")
print(run(ssh, f"mkdir -p {SERVER_ROOT}/logs/agent_progress && echo ok"))

# Clear backend pycache
print("\n=== Clearing pycache ===")
print(run(ssh, f"find {SERVER_ROOT}/backend -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; find {SERVER_ROOT}/backend -name '*.pyc' -delete 2>/dev/null; echo cleared"))

# Verify import works from correct path
print("\n=== Verify import from /var/www/html ===")
r = run(ssh, f"""cd {SERVER_ROOT} && python3 -c "
import sys; sys.path.insert(0,'.')
from backend.routes.agent_profile_routes import agent_profile_bp
print('agent_profile_bp OK:', agent_profile_bp.name)
from backend.services.agent_db_service import agent_db_service
print('agent_db_service OK')
" 2>&1""", timeout=20)
print(r)

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

ssh.close()
print("\nDone.")
