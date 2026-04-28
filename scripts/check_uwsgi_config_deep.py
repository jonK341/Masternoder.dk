"""Deep check of uWSGI configuration and which files it's using."""
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

print("=== Find running uwsgi process and its cmdline ===")
print(run(ssh, "ps aux | grep uwsgi | grep -v grep | head -5"))
print(run(ssh, "cat /proc/$(pgrep -f 'uwsgi.*master' | head -1)/cmdline 2>/dev/null | tr '\\0' ' ' | head -c 500"))

print("\n=== /var/www/html/wsgi.py full content ===")
print(run(ssh, "cat /var/www/html/wsgi.py"))

print("\n=== /var/www/html/vidgenerator/uwsgi.ini ===")
print(run(ssh, "cat /var/www/html/vidgenerator/uwsgi.ini"))

print("\n=== Check missing_endpoints_routes.py agents section at /var/www/html ===")
print(run(ssh, "grep -n 'agents_my_agents\\|agents/my-agents\\|def agents_' /var/www/html/backend/routes/missing_endpoints_routes.py | head -10"))

print("\n=== Check pycache for missing_endpoints_routes ===")
print(run(ssh, "ls -la /var/www/html/backend/routes/__pycache__/missing_endpoints* 2>/dev/null || echo 'no pycache'"))

ssh.close()
