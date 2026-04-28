"""Test agent endpoints on production via HTTPS."""
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

print("Test /api/agents/my-agents (HTTPS):")
r = run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user' 2>&1 | head -c 600")
print(r)

print("\nTest /api/agents/activity-feed (HTTPS):")
r2 = run(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/api/agents/activity-feed?user_id=default_user' 2>&1 | head -c 400")
print(r2)

print("\nCheck if blueprint registered in uwsgi log:")
r3 = run(ssh, "grep -i 'agent_profile' /var/log/uwsgi/app/*.log 2>/dev/null | tail -5 || grep -i 'agent_profile' /var/www/html/vidgenerator/flask_app.log 2>/dev/null | tail -5 || echo 'no log found'")
print(r3)

ssh.close()
