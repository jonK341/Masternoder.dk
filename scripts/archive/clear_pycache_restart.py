"""Clear Python pycache and do a clean uWSGI restart."""
import paramiko, os, time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run(ssh, cmd, timeout=30):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())\

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== Clearing pycache ===")
print(run(ssh, f"find {BASE_REMOTE}/backend -name '__pycache__' -type d -exec rm -rf {{}} + 2>/dev/null; echo cleared"))
print(run(ssh, f"find {BASE_REMOTE}/backend -name '*.pyc' -delete 2>/dev/null; echo pyc_cleared"))

print("\n=== Stop uWSGI ===")
print(run(ssh, "systemctl stop uwsgi 2>&1 && echo stopped", timeout=15))
time.sleep(2)

print("\n=== Start uWSGI ===")
print(run(ssh, "systemctl start uwsgi 2>&1 && echo started", timeout=15))
time.sleep(8)

print("Status:", run(ssh, "systemctl is-active uwsgi"))

print("\n=== Test endpoints ===")
r1 = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500")
print("my-agents:", r1)
r2 = run(ssh, f"curl -s 'http://127.0.0.1:5000/vidgenerator/api/agents/activity-feed?user_id=default_user' 2>&1 | head -c 300")
print("activity-feed:", r2)

# Also test via HTTPS
print("\n=== HTTPS test ===")
print(run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500"))

ssh.close()
print("\nDone.")
