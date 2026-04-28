"""Check Flask URL map for None endpoint routes."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

REMOTE_SCRIPT = r"""
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()
print('=== URL rules without /api/ containing agent ===')
for rule in sorted(app.url_map.iter_rules(), key=lambda x: x.rule):
    if 'agent' in rule.rule.lower() and '/api/' not in rule.rule:
        vf = app.view_functions.get(rule.endpoint)
        print('  ' + repr(rule.rule) + ' -> ep=' + repr(rule.endpoint) + ' -> vf=' + repr(vf))
print('=== Endpoint None rules ===')
for rule in app.url_map.iter_rules():
    if rule.endpoint is None:
        print('  NONE: ' + repr(rule.rule))
print('DONE')
"""

def run_cmd(ssh, cmd, timeout=30):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip(), e.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    # Write script to server
    import io
    sftp.putfo(io.BytesIO(REMOTE_SCRIPT.encode()), '/tmp/check_url_map.py')
    sftp.close()

    out, err = run_cmd(ssh, 'cd /var/www/html/vidgenerator && .venv/bin/python /tmp/check_url_map.py 2>&1 | grep -E "agent|NONE|DONE|ERROR" | head -30')
    print(out)
    if err:
        print('STDERR:', err[:500])

    ssh.close()

if __name__ == '__main__':
    main()
