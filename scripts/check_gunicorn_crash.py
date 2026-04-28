"""Check Gunicorn crash logs and service file on production server."""
import paramiko
import os
import sys

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    print("=== Gunicorn service file ===")
    out, _ = run_cmd(ssh, "cat /etc/systemd/system/vidgenerator-gunicorn.service 2>/dev/null")
    print(out or "(not found)")

    print("\n=== uWSGI service file ===")
    out, _ = run_cmd(ssh, "cat /etc/systemd/system/uwsgi-vidgenerator.service 2>/dev/null")
    print(out or "(not found)")

    print("\n=== Gunicorn crash logs (last 50 lines) ===")
    out, _ = run_cmd(ssh, "journalctl -u vidgenerator-gunicorn --no-pager -n 50 2>/dev/null")
    print(out or "(no logs)")

    print("\n=== UWSGi logs (last 20 lines) ===")
    out, _ = run_cmd(ssh, "journalctl -u uwsgi-vidgenerator --no-pager -n 20 2>/dev/null")
    print(out or "(no logs)")

    print("\n=== App logs directory ===")
    out, _ = run_cmd(ssh, "ls -la /var/www/html/vidgenerator/logs/ 2>/dev/null | head -10")
    print(out or "(none)")

    out, _ = run_cmd(ssh, "tail -30 /var/www/html/vidgenerator/logs/flask_app.log 2>/dev/null")
    print("\n=== Flask app log (last 30 lines) ===")
    print(out or "(not found)")

    ssh.close()

if __name__ == "__main__":
    main()
