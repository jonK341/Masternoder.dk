"""Force full uWSGI restart: kill all workers, wait, start fresh."""
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

    print("=== Current worker PIDs ===")
    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | awk '{print $1, $2, $11}' | head -10")
    print(out)

    print("\n=== uwsgi.ini config ===")
    out = run_cmd(ssh, f"cat {BASE_REMOTE}/uwsgi.ini")
    print(out)

    print("\n=== Stopping via systemctl + pkill ===")
    run_cmd(ssh, "systemctl stop uwsgi-vidgenerator 2>/dev/null || true")
    time.sleep(3)
    run_cmd(ssh, "pkill -9 -f uwsgi 2>/dev/null || true")
    time.sleep(3)

    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | wc -l")
    print(f"  uWSGI processes after kill: {out}")

    print("\n=== Starting fresh ===")
    out = run_cmd(ssh, "systemctl start uwsgi-vidgenerator 2>&1")
    print(f"  Start: {out or 'OK'}")
    time.sleep(15)

    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | awk '{print $1, $2, $11}' | head -6")
    print(f"New workers:\n{out}")

    out = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
    print(f"Service: {out}")

    print("\n=== Smoke tests ===")
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/',
    ]:
        out = run_cmd(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    print("\n=== Log tail ===")
    out = run_cmd(ssh, f"tail -8 {BASE_REMOTE}/uwsgi.log 2>/dev/null")
    print(out)

    ssh.close()
    print("\nDone.")

if __name__ == '__main__':
    main()
