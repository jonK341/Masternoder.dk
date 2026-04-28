"""Check Python setup and video generation on production server."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=30):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    return stdout.read().decode().strip(), stderr.read().decode().strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=10)

    print("=== Python paths ===")
    out, _ = run_cmd(ssh, "which python python3 /var/www/html/vidgenerator/.venv/bin/python 2>/dev/null")
    print(out)

    print("\n=== Server venv MoviePy ===")
    out, err = run_cmd(ssh, "/var/www/html/vidgenerator/.venv/bin/python -c 'import moviepy; print(moviepy.__version__)' 2>&1")
    print(out or err)

    print("\n=== App Python path ===")
    out, err = run_cmd(ssh, "cat /etc/systemd/system/vidgenerator*.service 2>/dev/null | grep -i python | head -5")
    print(out or err)
    out, err = run_cmd(ssh, "cat /var/www/html/vidgenerator/start.bat 2>/dev/null | head -5")
    print(out or err)
    out, err = run_cmd(ssh, "ls /var/www/html/vidgenerator/.venv/bin/ 2>/dev/null | head -20")
    print(out or "no venv found")

    print("\n=== App running process ===")
    out, _ = run_cmd(ssh, "ps aux | grep -i gunicorn | grep -v grep | head -3")
    print(out)

    ssh.close()

if __name__ == "__main__":
    main()
