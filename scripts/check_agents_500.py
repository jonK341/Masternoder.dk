"""Find root cause of /agents/ 500 error."""
import paramiko
import os

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=20):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    # Check uwsgi log for the 500
    out, _ = run_cmd(ssh, "tail -40 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | tail -40")
    print("--- uwsgi.log ---")
    print(out[-2000:] if len(out) > 2000 else out)

    # Check if agents html exists at server path
    out2, _ = run_cmd(ssh, "ls -la /var/www/html/vidgenerator/vidgenerator/agents/")
    print("\n--- agents dir ---")
    print(out2)

    # Confirm PAGES list in all_page_routes
    out3, _ = run_cmd(ssh, "grep -n 'agents' /var/www/html/vidgenerator/backend/routes/all_page_routes.py")
    print("\n--- all_page_routes agents ---")
    print(out3)

    ssh.close()

if __name__ == "__main__":
    main()
