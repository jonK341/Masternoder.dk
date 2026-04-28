"""Deploy all_page_routes fix + restart."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))
BASE_LOCAL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_REMOTE = "/var/www/html/vidgenerator"

def run_cmd(ssh, cmd, timeout=25):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)
    sftp = ssh.open_sftp()

    local = os.path.join(BASE_LOCAL, 'backend', 'routes', 'all_page_routes.py')
    remote = f"{BASE_REMOTE}/backend/routes/all_page_routes.py"
    sftp.put(local, remote)
    print(f"Uploaded: all_page_routes.py")
    sftp.close()

    out, err = run_cmd(ssh, "systemctl reload vidgenerator 2>/dev/null || systemctl restart vidgenerator 2>/dev/null || touch /var/www/html/vidgenerator/uwsgi.ini")
    print(f"Restart: {out or 'ok'} {err or ''}")

    import time; time.sleep(5)
    out2, _ = run_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' https://masternoder.dk/vidgenerator/agents/ 2>/dev/null || curl -ks -o /dev/null -w '%{http_code}' https://masternoder.dk/vidgenerator/agents/ 2>/dev/null")
    print(f"HTTP /vidgenerator/agents/: {out2}")
    ssh.close()
    print("Done.")

if __name__ == "__main__":
    main()
