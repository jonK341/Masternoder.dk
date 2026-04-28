"""Wait for service to be fully up, then read the exact 500 error."""
import paramiko
import os
import time

SERVER_HOST = "masternoder.dk"
SERVER_USER = "root"
SERVER_PASS = (os.getenv('DEPLOY_PASS') or '').strip() or (_ for _ in ()).throw(SystemExit('Set DEPLOY_PASS for SSH.'))

def run_cmd(ssh, cmd, timeout=20):
    _, o, e = ssh.exec_command(cmd, timeout=timeout)
    return o.read().decode(errors='replace').strip(), e.read().decode(errors='replace').strip()

def main():
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(SERVER_HOST, username=SERVER_USER, password=SERVER_PASS, timeout=15)

    # Wait for active
    for i in range(8):
        out, _ = run_cmd(ssh, 'systemctl is-active uwsgi-vidgenerator 2>/dev/null || systemctl is-active vidgenerator 2>/dev/null')
        print(f'  [{i+1}] status: {out}')
        if 'active' in out and 'deactivating' not in out and 'activating' not in out:
            break
        time.sleep(3)

    # Trigger the 500 so it logs
    run_cmd(ssh, "curl -sk 'https://masternoder.dk/vidgenerator/agents/' > /dev/null 2>&1", timeout=10)
    time.sleep(1)

    # Read the log
    out, _ = run_cmd(ssh, 'tail -60 /var/www/html/vidgenerator/uwsgi.log 2>/dev/null | tail -60')
    print('\n--- uwsgi.log (last 60 lines) ---')
    print(out)

    ssh.close()

if __name__ == '__main__':
    main()
