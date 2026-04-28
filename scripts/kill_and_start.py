"""Kill uWSGI processes individually then start fresh."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def exec_nowait(ssh, cmd):
    """Fire-and-forget: don't wait for output."""
    transport = ssh.get_transport()
    ch = transport.open_session()
    ch.exec_command(cmd)
    ch.close()

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=== Killing uWSGI workers with SIGKILL ===")
    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | awk '{print $2}'")
    pids = [p.strip() for p in out.splitlines() if p.strip().isdigit()]
    print(f"  PIDs to kill: {pids}")
    for pid in pids:
        exec_nowait(ssh, f"kill -9 {pid} 2>/dev/null")
    time.sleep(2)

    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | wc -l")
    print(f"  Remaining: {out}")

    print("\n=== Starting uwsgi-vidgenerator ===")
    exec_nowait(ssh, "systemctl start uwsgi-vidgenerator")
    time.sleep(15)

    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | awk '{print $2}' | head -6")
    print(f"New PIDs:\n{out}")

    print("\n=== Smoke tests ===")
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/',
    ]:
        out = run_cmd(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    print("\n=== Log tail ===")
    out = run_cmd(ssh, f"tail -6 {BASE_REMOTE}/uwsgi.log")
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()
