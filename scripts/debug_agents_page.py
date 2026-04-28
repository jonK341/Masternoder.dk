"""Debug agents page 500 error."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=15):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    out, err = run_cmd(ssh, "curl -sv http://localhost/vidgenerator/agents/ 2>&1 | tail -30")
    print(out[:2000])

    # Check flask app log for 500 details
    out2, _ = run_cmd(ssh, "tail -20 /var/www/html/vidgenerator/flask_app.log 2>/dev/null || tail -20 /var/log/uwsgi/uwsgi.log 2>/dev/null || echo 'no log'")
    print("\n--- FLASK LOG ---")
    print(out2)

    ssh.close()

if __name__ == "__main__":
    main()
