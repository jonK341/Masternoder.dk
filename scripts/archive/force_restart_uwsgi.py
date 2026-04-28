"""Force restart uWSGI if stuck in deactivating state."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=10):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    out, _ = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
    print(f"Current status: {out}")

    if 'deactivating' in out or 'inactive' in out:
        print("Force stopping uWSGI workers...")
        run_cmd(ssh, "systemctl kill --signal=SIGKILL uwsgi-vidgenerator 2>/dev/null || killall -9 uwsgi-core 2>/dev/null || true")
        time.sleep(2)
        run_cmd(ssh, "systemctl start uwsgi-vidgenerator 2>/dev/null")
        time.sleep(3)
        out, _ = run_cmd(ssh, "systemctl is-active uwsgi-vidgenerator 2>/dev/null")
        print(f"After force restart: {out}")

    out, _ = run_cmd(ssh, "ps aux | grep uwsgi | grep -v grep | wc -l")
    print(f"uWSGI processes: {out}")

    # Test the app
    out, _ = run_cmd(ssh, "curl -s -o /dev/null -w '%{http_code}' http://localhost:5000/ 2>/dev/null || curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:5000/ 2>/dev/null")
    print(f"HTTP response: {out}")

    ssh.close()

if __name__ == "__main__":
    main()
