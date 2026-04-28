"""Find what handles /agents/ and returns None in the live app."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

REMOTE_SCRIPT = """
import sys
sys.path.insert(0, '/var/www/html/vidgenerator')
from src.app import create_app
app = create_app()

# Find what matches /agents/ and /vidgenerator/agents/
for test_url in ['/agents/', '/vidgenerator/agents/']:
    try:
        with app.test_request_context(test_url):
            from flask import request
            adapter = app.url_map.bind('masternoder.dk')
            ep, args = adapter.match(test_url, method='GET')
            vf = app.view_functions.get(ep)
            print(f'URL={test_url!r} -> endpoint={ep!r} -> vf={vf!r}')
            if vf:
                import inspect
                try:
                    src_file = inspect.getfile(vf)
                    src_line = inspect.getsourcelines(vf)[1]
                    print(f'  defined at: {src_file}:{src_line}')
                except Exception as e2:
                    print(f'  source lookup failed: {e2}')
    except Exception as e:
        print(f'URL={test_url!r} -> ERROR: {e}')
print('DONE')
"""

def run_cmd(ssh, cmd, timeout=30):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    import io
    sftp.putfo(io.BytesIO(REMOTE_SCRIPT.encode()), '/tmp/find_none_route.py')
    sftp.close()

    out = run_cmd(ssh, 'cd /var/www/html/vidgenerator && .venv/bin/python /tmp/find_none_route.py 2>&1 | grep -E "URL=|DONE|ERROR|defined at|endpoint" | head -20')
    print(out)
    ssh.close()

if __name__ == '__main__':
    main()
