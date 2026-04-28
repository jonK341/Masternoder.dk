"""Deploy all_page_routes fix (dedicated agents route) and restart."""
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

    local = os.path.join(BASE_LOCAL, 'backend', 'routes', 'all_page_routes.py')
    sftp.put(local, f'{BASE_REMOTE}/backend/routes/all_page_routes.py')
    print('Uploaded: all_page_routes.py')
    sftp.close()

    print('Restarting uWSGI...')
    try:
        ssh.exec_command('systemctl restart uwsgi-vidgenerator', timeout=5)
    except Exception:
        pass
    ssh.close()

    print('Waiting 10s for workers...')
    time.sleep(10)

    ssh2 = paramiko.SSHClient()
    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh2.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    out = run_cmd(ssh2, 'systemctl is-active uwsgi-vidgenerator 2>/dev/null')
    print(f'Service: {out}')

    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/profile/',
    ]:
        out = run_cmd(ssh2, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    ssh2.close()
    print('Done.')

if __name__ == '__main__':
    main()
