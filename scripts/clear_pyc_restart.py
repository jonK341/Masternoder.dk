"""Clear .pyc cache, force fresh reload, verify agents page."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=30):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=== Clearing stale .pyc / __pycache__ ===")
    out = run_cmd(ssh, f"find {BASE_REMOTE}/backend/routes/__pycache__ -name 'all_page*' -delete 2>/dev/null; echo cleared")
    print(f"  routes pyc: {out}")
    out = run_cmd(ssh, f"find {BASE_REMOTE}/backend/__pycache__ -name '*.pyc' -delete 2>/dev/null; echo cleared")
    print(f"  backend pyc: {out}")
    out = run_cmd(ssh, f"find {BASE_REMOTE} -name '__pycache__' -type d | xargs rm -rf 2>/dev/null; echo all cleared")
    print(f"  all pycache: {out}")

    print("\n=== Hard killing all uWSGI workers ===")
    out = run_cmd(ssh, "pkill -9 -f uwsgi 2>/dev/null; echo killed")
    print(f"  pkill: {out}")
    time.sleep(3)

    print("=== Starting uWSGI fresh ===")
    out = run_cmd(ssh, "systemctl start uwsgi-vidgenerator 2>&1 || systemctl restart uwsgi-vidgenerator 2>&1")
    print(f"  start: {out}")
    time.sleep(12)

    print("=== Waiting for active status ===")
    for i in range(10):
        out = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
        print(f"  [{i+1}] {out}")
        if out == 'active':
            break
        time.sleep(3)

    print("\n=== Smoke tests ===")
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/',
        'https://masternoder.dk/vidgenerator/profile/',
    ]:
        out = run_cmd(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    print("\n=== Fresh log tail ===")
    out = run_cmd(ssh, f"tail -10 {BASE_REMOTE}/uwsgi.log 2>/dev/null")
    print(out)

    ssh.close()
    print("\nDone.")

if __name__ == '__main__':
    main()
