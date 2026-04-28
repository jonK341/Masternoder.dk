"""Force restart uWSGI and test agent endpoints."""
import paramiko, time, os

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

print("uWSGI status:", run(ssh, "systemctl is-active uwsgi 2>&1"))
print("Restarting:  ", run(ssh, "systemctl restart uwsgi 2>&1 && echo OK", timeout=30))
time.sleep(5)
print("Status after:", run(ssh, "systemctl is-active uwsgi 2>&1"))

print("\nTest /api/agents/my-agents:")
print(run(ssh, "curl -s 'http://localhost/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 400"))

print("\nTest /api/agents/activity-feed:")
print(run(ssh, "curl -s 'http://localhost/vidgenerator/api/agents/activity-feed?user_id=default_user' 2>&1 | head -c 400"))

ssh.close()
print("\nDone.")
