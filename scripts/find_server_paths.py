"""Find the actual paths used by the production server."""
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

# Check what parent dir contains
print("=== /var/www/html contents ===")
print(run(ssh, "ls /var/www/html/"))

print("\n=== /var/www/html/backend contents ===")
print(run(ssh, "ls /var/www/html/backend/ 2>/dev/null || echo 'NO backend at /var/www/html/'"))

print("\n=== find all register_blueprints.py ===")
print(run(ssh, "find /var/www/html -name 'register_blueprints.py' 2>/dev/null"))

print("\n=== Check wsgi.py actual path resolution ===")
print(run(ssh, """python3 -c "
import os
this_dir = '/var/www/html/vidgenerator'
project_root = os.path.dirname(this_dir)
print('this_dir:', this_dir)
print('project_root:', project_root)
print('project_root/backend exists:', os.path.isdir(os.path.join(project_root, 'backend')))
print('this_dir/backend exists:', os.path.isdir(os.path.join(this_dir, 'backend')))
" 2>&1"""))

print("\n=== /var/www/html/src contents ===")
print(run(ssh, "ls /var/www/html/src/ 2>/dev/null || echo 'NO src at /var/www/html/'"))

ssh.close()
