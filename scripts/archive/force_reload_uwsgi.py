"""Force uWSGI to reload by touching wsgi file, then verify agent routes live."""
import paramiko, os, time

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

# Find wsgi entry point
print("=== Find wsgi/app files ===")
print(run(ssh, f"find {BASE_REMOTE} -maxdepth 3 -name '*.ini' -o -name 'wsgi.py' -o -name 'uwsgi.ini' 2>/dev/null | head -10"))

# Try hard restart options
print("\n=== Hard stop + start ===")
print(run(ssh, "systemctl stop uwsgi 2>&1 && sleep 2 && systemctl start uwsgi 2>&1 && echo 'restarted'", timeout=30))
time.sleep(6)

print("Status:", run(ssh, "systemctl is-active uwsgi"))

# Test
print("\n=== Live test ===")
print(run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 500"))
print(run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/activity-feed?user_id=default_user' 2>&1 | head -c 300"))

ssh.close()
print("Done.")
