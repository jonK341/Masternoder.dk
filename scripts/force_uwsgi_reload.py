"""Force uWSGI to reload all workers and verify agents page."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    print("=== uWSGI process status ===")
    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | head -5")
    print(out)

    print("\n=== Forcing uwsgi reload (touch + SIGHUP) ===")
    # Method 1: touch uwsgi.ini to trigger reload
    run_cmd(ssh, f"touch {BASE_REMOTE}/uwsgi.ini")
    print("  Touched uwsgi.ini")

    # Method 2: send SIGHUP to master process for graceful reload
    out = run_cmd(ssh, "cat /tmp/uwsgi-vidgenerator.pid 2>/dev/null || cat /var/run/uwsgi-vidgenerator.pid 2>/dev/null || pgrep -f 'uwsgi.*vidgenerator' | head -1")
    pid = out.strip()
    if pid and pid.isdigit():
        run_cmd(ssh, f"kill -HUP {pid}")
        print(f"  Sent SIGHUP to PID {pid}")
    else:
        print(f"  No PID found ({pid!r}), trying pkill -HUP")
        run_cmd(ssh, "pkill -HUP -f 'uwsgi'")

    print("  Waiting 8s for reload...")
    time.sleep(8)

    print("\n=== After reload ===")
    out = run_cmd(ssh, "ps aux | grep '[u]wsgi' | wc -l")
    print(f"  uWSGI processes: {out}")

    out = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
    print(f"  Systemd status: {out}")

    print("\n=== Smoke tests ===")
    for url in [
        'https://masternoder.dk/vidgenerator/agents/',
        'https://masternoder.dk/vidgenerator/api/agents/my-agents?user_id=default_user',
        'https://masternoder.dk/vidgenerator/',
    ]:
        out = run_cmd(ssh, f"curl -sk -o /dev/null -w '%{{http_code}}' '{url}'", timeout=15)
        print(f'  [{out}] {url}')

    # Show any error from fresh log
    print("\n=== Latest log errors ===")
    out = run_cmd(ssh, f"tail -15 {BASE_REMOTE}/uwsgi.log 2>/dev/null")
    print(out)

    ssh.close()
    print("\nDone.")

if __name__ == '__main__':
    main()
