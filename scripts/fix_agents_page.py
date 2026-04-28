"""Check the 500 error on /agents/ and redeploy all_page_routes with the fix."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    print("=== Uploading all agent system files ===")
    files = [
        ('backend/routes/all_page_routes.py',      f'{BASE_REMOTE}/backend/routes/all_page_routes.py'),
        ('backend/register_blueprints.py',          f'{BASE_REMOTE}/backend/register_blueprints.py'),
        ('backend/services/agent_db_service.py',    f'{BASE_REMOTE}/backend/services/agent_db_service.py'),
        ('backend/routes/agent_profile_routes.py',  f'{BASE_REMOTE}/backend/routes/agent_profile_routes.py'),
        ('backend/routes/shop_routes.py',           f'{BASE_REMOTE}/backend/routes/shop_routes.py'),
        ('backend/routes/hunters_game.py',          f'{BASE_REMOTE}/backend/routes/hunters_game.py'),
        ('vidgenerator/profile/index.html',         f'{BASE_REMOTE}/vidgenerator/profile/index.html'),
        ('vidgenerator/agents/index.html',          f'{BASE_REMOTE}/vidgenerator/agents/index.html'),
    ]
    run_cmd(ssh, f'mkdir -p {BASE_REMOTE}/vidgenerator/agents')
    for local_rel, remote in files:
        local = os.path.join(BASE_LOCAL, local_rel)
        sftp.put(local, remote)
        print(f'  Uploaded: {os.path.basename(local)}')
    sftp.close()

    print('\n=== Restarting uWSGI ===')
    try:
        ssh.exec_command('systemctl restart uwsgi-vidgenerator', timeout=5)
    except Exception:
        pass

    ssh.close()
    print('  Restart sent. Waiting 8s...')
    time.sleep(8)

    # Reconnect and verify
    ssh2 = paramiko.SSHClient()
    ssh2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh2.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    out, _ = run_cmd(ssh2, 'systemctl is-active uwsgi-vidgenerator 2>/dev/null || systemctl is-active vidgenerator 2>/dev/null')
    print(f'  uWSGI status: {out}')

    # Check uwsgi log for errors
    out, _ = run_cmd(ssh2, 'tail -30 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | grep -i "error\\|exception\\|agents" | tail -10')
    print(f'\n--- Recent errors in uwsgi.log ---\n{out}')

    print('\n=== Smoke tests ===')
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/api/agents/activity-feed?user_id=default_user',
    ]:
        out, _ = run_cmd(ssh2, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    ssh2.close()
    print('\nDone.')

if __name__ == '__main__':
    main()
