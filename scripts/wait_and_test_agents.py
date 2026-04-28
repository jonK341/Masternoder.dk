"""Wait for service to be fully active then test agents page."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    # Poll until active
    for i in range(15):
        out = run_cmd(ssh, 'systemctl is-active uwsgi-vidgenerator 2>/dev/null')
        print(f'  [{i+1}] {out}')
        if out == 'active':
            break
        time.sleep(3)

    print()
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/profile/',
        'https://masternoder.dk/vidgenerator/',
    ]:
        out = run_cmd(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    # If still 500, get the fresh error
    out = run_cmd(ssh, "tail -20 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | grep -A5 'agents'")
    if out:
        print(f'\n--- agents errors ---\n{out}')

    ssh.close()

if __name__ == '__main__':
    main()
