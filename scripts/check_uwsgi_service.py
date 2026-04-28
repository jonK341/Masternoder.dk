"""Check which wsgi.py and register_blueprints.py the live server actually uses."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run(ssh, cmd, timeout=20):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())\

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== systemd uwsgi service file ===")
print(run(ssh, "cat /etc/systemd/system/uwsgi.service 2>/dev/null || systemctl cat uwsgi 2>/dev/null | head -30"))

print("\n=== /etc/uwsgi/apps-enabled ===")
print(run(ssh, "ls /etc/uwsgi/apps-enabled/ 2>/dev/null && cat /etc/uwsgi/apps-enabled/*.ini 2>/dev/null | head -30 || echo none"))

print("\n=== /var/www/html/wsgi.py ===")
print(run(ssh, "cat /var/www/html/wsgi.py 2>/dev/null | head -30"))

print("\n=== Which register_blueprints has agent_profile? ===")
print(run(ssh, "grep -l 'agent_profile' /var/www/html/backend/register_blueprints.py /var/www/html/vidgenerator/backend/register_blueprints.py 2>/dev/null"))

print("\n=== Check if missing_endpoints_routes has agent routes ===")
print(run(ssh, "grep -c 'agents_my_agents\\|agents/my-agents' /var/www/html/backend/routes/missing_endpoints_routes.py 2>/dev/null"))

ssh.close()
