"""Find which register_blueprints.py is actually used."""
import paramiko, os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
SERVER_ROOT = "/var/www/html"

def run(ssh, cmd, timeout=25):
    _, out, err = ssh.exec_command(cmd, timeout=timeout)
    return (out.read().decode('utf-8', errors='replace').strip() +
            err.read().decode('utf-8', errors='replace').strip())\

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

print("=== src/app.py - how it calls register ===")
print(run(ssh, f"grep -n 'register_blueprint\\|register_all\\|import.*register' {SERVER_ROOT}/src/app.py | head -20"))

print("\n=== check agent_profile in /var/www/html/backend/register_blueprints.py ===")
print(run(ssh, f"grep -n 'agent_profile' {SERVER_ROOT}/backend/register_blueprints.py | head -5"))

print("\n=== What file is imported as backend.register_blueprints? ===")
r = run(ssh, f"""cd {SERVER_ROOT} && python3 -c "
import sys; sys.path.insert(0,'.')
import backend.register_blueprints as rb
print('File loaded:', rb.__file__)
" 2>&1""", timeout=15)
print(r)

print("\n=== route_loader.py (if any) ===")
print(run(ssh, f"cat {SERVER_ROOT}/backend/route_loader.py 2>/dev/null | head -40"))

ssh.close()
