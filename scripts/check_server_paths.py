"""Check server module paths."""
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

print("find account_resolution:")
print(run(ssh, "find /var/www/html/vidgenerator -name 'account_resolution*' 2>/dev/null"))

print("\nfind points_routes:")
print(run(ssh, "find /var/www/html/vidgenerator -name 'points_routes*' 2>/dev/null"))

print("\nHow do other blueprints import resolve_user_id?")
print(run(ssh, "grep -r 'resolve_user_id' /var/www/html/vidgenerator/backend/routes/ 2>/dev/null | head -5"))

ssh.close()
