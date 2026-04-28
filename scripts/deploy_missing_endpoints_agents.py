"""Deploy missing_endpoints_routes with agents page route and reload."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    local = os.path.join(BASE_LOCAL, 'backend', 'routes', 'missing_endpoints_routes.py')
    sftp.put(local, f'{BASE_REMOTE}/backend/routes/missing_endpoints_routes.py')
    print('Uploaded: missing_endpoints_routes.py')
    sftp.close()

    # Clear pyc for this file
    run_cmd(ssh, f'find {BASE_REMOTE}/backend/routes/__pycache__ -name "missing_endpoints*" -delete 2>/dev/null')
    print('Cleared pyc')

    print('Sending SIGHUP to master uWSGI...')
    pid = run_cmd(ssh, 'pgrep -f "uwsgi.*master" | head -1 || ps aux | grep "[u]wsgi" | grep -v grep | awk \'{print $2}\' | head -1')
    if pid and pid.isdigit():
        run_cmd(ssh, f'kill -HUP {pid}')
        print(f'  SIGHUP sent to PID {pid}')
    else:
        print(f'  No master PID ({pid!r}), trying FIFO...')
        run_cmd(ssh, f'touch {BASE_REMOTE}/uwsgi.ini')
    
    time.sleep(8)

    print('\n=== Smoke tests ===')
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/',
        'https://masternoder.dk/vidgenerator/profile/',
    ]:
        out = run_cmd(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    print('\n=== Log errors ===')
    out = run_cmd(ssh, f"tail -5 {BASE_REMOTE}/uwsgi.log 2>/dev/null")
    print(out)

    ssh.close()
    print('\nDone.')

if __name__ == '__main__':
    main()
